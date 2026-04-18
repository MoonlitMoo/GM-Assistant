class Users::RegistrationsController < Devise::RegistrationsController
  before_action :configure_sign_up_params, only: :create

  def create
    @invite_token = params.dig(resource_name, :invite_token).to_s.strip
    invite_code = InviteCode.unused.find_by(token: @invite_token)

    unless invite_code
      build_resource(sign_up_params.except(:invite_token))
      clean_up_passwords(resource)
      set_minimum_password_length
      flash.now[:alert] = "Invite code is invalid or has already been used."
      render :new, status: :unprocessable_entity
      return
    end

    strip_invite_token!

    super do |resource|
      invite_code.use!(resource) if resource.persisted?
    end
  end

  def edit
    redirect_to edit_settings_path(settings_navigation_params), status: Devise.responder.redirect_status
  end

  def update
    self.resource = resource_class.to_adapter.get!(send(:"current_#{resource_name}").to_key)
    prev_unconfirmed_email = resource.unconfirmed_email if resource.respond_to?(:unconfirmed_email)

    resource_updated = update_resource(resource, account_update_params)
    yield resource if block_given?

    if resource_updated
      set_flash_message_for_update(resource, prev_unconfirmed_email)
      bypass_sign_in resource, scope: resource_name if sign_in_after_change_password?
      respond_with resource, location: after_update_path_for(resource)
    else
      clean_up_passwords resource
      prepare_settings_page(resource)
      render "settings/edit", status: :unprocessable_entity
    end
  end

  protected

  def configure_sign_up_params
    devise_parameter_sanitizer.permit(:sign_up, keys: [ :invite_token ])
  end

  def after_update_path_for(_resource)
    edit_settings_path(settings_navigation_params)
  end

  private

  def strip_invite_token!
    params[resource_name]&.delete(:invite_token)
  end

  def prepare_settings_page(account_user = current_user)
    @preferences_user = resource_class.find(current_user.id)
    @account_user = account_user
    @minimum_password_length = resource_class.password_length.min if resource_class.respond_to?(:password_length)
  end

  def settings_navigation_params
    return_to = safe_return_to_path(params[:return_to])
    return_to.present? ? { return_to: return_to } : {}
  end

  def safe_return_to_path(path)
    value = path.to_s
    return if value.blank?
    return if value.start_with?("//")
    return unless value.start_with?("/")
    return if value.match?(/[\r\n]/)

    value
  end
end
