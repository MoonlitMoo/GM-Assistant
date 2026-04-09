class SettingsController < ApplicationController
  def edit
  end

  def update
    if Current.user.update(user_preferences_params)
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

  def settings_navigation_params
    return_to = safe_return_to_path(params[:return_to])
    return_to.present? ? { return_to: return_to } : {}
  end

  def sync_existing_player_displays!
    PlayerDisplay.joins(:campaign)
                 .where(campaigns: { user_id: Current.user.id })
                 .update_all(
                   transition_type: PlayerDisplay.transition_types.fetch(Current.user.default_transition),
                   image_fit: Current.user.image_fit,
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
