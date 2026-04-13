class Users::RegistrationsController < Devise::RegistrationsController
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

  def after_update_path_for(_resource)
    edit_settings_path(settings_navigation_params)
  end

  private

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
