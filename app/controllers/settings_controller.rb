class SettingsController < ApplicationController
  before_action :prepare_settings_page

  def edit
  end

  def update
    @preferences_user.assign_attributes(user_preferences_params)

    if @preferences_user.save
      sync_existing_player_displays!
      redirect_to edit_settings_path(settings_navigation_params), notice: "Settings saved."
    else
      render :edit, status: :unprocessable_entity
    end
  end

  private

  def user_preferences_params
    params.permit(
      :default_transition,
      :default_show_title,
      :crossfade_duration,
      :dashboard_recent_count,
      :gm_history_count,
      :image_fit
    )
  end

  def prepare_settings_page
    @preferences_user = current_user
    @account_user = User.find(current_user.id)
    @minimum_password_length = User.password_length.min if User.respond_to?(:password_length)
  end

  def settings_navigation_params
    return_to = safe_return_to_path(params[:return_to])
    return_to.present? ? { return_to: return_to } : {}
  end

  def sync_existing_player_displays!
    PlayerDisplay.joins(:campaign)
                 .where(campaigns: { user_id: current_user.id })
                 .update_all(
                   transition_type: PlayerDisplay.transition_types.fetch(current_user.default_transition),
                   image_fit: current_user.image_fit,
                   updated_at: Time.current
                 )
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
