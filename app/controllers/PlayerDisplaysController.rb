class PlayerDisplaysController < ApplicationController
  before_action :set_campaign
  after_action :touch_campaign_activity, only: [ :present, :clear, :toggle_title, :update_transition ]

  def present
    if params[:current_image_id].blank?
      respond_to do |format|
        format.json { render json: { errors: [ "current_image_id is required" ] }, status: :unprocessable_entity }
        format.turbo_stream { head :unprocessable_entity }
        format.html { head :unprocessable_entity }
      end
      return
    end

    @player_display = @campaign.player_display || @campaign.build_player_display
    previous_image = @player_display.current_image

    if previous_image&.id.to_s == params[:current_image_id].to_s
      respond_with_player_display(@player_display, broadcast: false)
      return
    end

    @player_display.current_image_id = params[:current_image_id]
    @player_display.show_title = @player_display.current_image.show_title if @player_display.current_image.present?

    if @player_display.valid?
      PlayerDisplay.transaction do
        record_presented_event!(previous_image) if previous_image.present?
        @player_display.save!
      end

      respond_with_player_display(@player_display)
    else
      respond_to do |format|
        format.json { render json: { errors: @player_display.errors.full_messages }, status: :unprocessable_entity }
        format.turbo_stream { head :unprocessable_entity }
        format.html { head :unprocessable_entity }
      end
    end
  rescue ActiveRecord::InvalidForeignKey
    respond_to do |format|
      format.json { render json: { errors: [ "Current image must exist" ] }, status: :unprocessable_entity }
      format.turbo_stream { head :unprocessable_entity }
      format.html { head :unprocessable_entity }
    end
  rescue ActiveRecord::RecordInvalid => error
    respond_to do |format|
      format.json { render json: { errors: error.record.errors.full_messages }, status: :unprocessable_entity }
      format.turbo_stream { head :unprocessable_entity }
      format.html { head :unprocessable_entity }
    end
  end

  def clear
    player_display = @campaign.player_display
    previous_image = player_display&.current_image

    PlayerDisplay.transaction do
      record_presented_event!(previous_image) if previous_image.present?
      player_display&.update!(current_image: nil)
      record_cleared_event!
    end

    payload = { cleared: true }

    ActionCable.server.broadcast(player_display_stream_name, payload)

    respond_to do |format|
      format.json { render json: payload }
      format.turbo_stream { render_gm_panel_turbo_stream(player_display) }
      format.html { render_gm_panel_turbo_stream(player_display) }
    end
  end

  def toggle_title
    player_display = @campaign.player_display || @campaign.build_player_display
    player_display.show_title = !player_display.show_title
    player_display.save!

    payload = { show_title: player_display.show_title }

    ActionCable.server.broadcast(player_display_stream_name, payload)

    respond_to do |format|
      format.json { render json: payload }
      format.turbo_stream { render_gm_panel_controls_turbo_stream(player_display) }
      format.html { render_gm_panel_controls_turbo_stream(player_display) }
    end
  end

  def update_transition
    if params[:transition_type].blank?
      respond_to do |format|
        format.json { render json: { errors: [ "transition_type is required" ] }, status: :unprocessable_entity }
        format.turbo_stream { head :unprocessable_entity }
        format.html { head :unprocessable_entity }
      end
      return
    end

    player_display = @campaign.player_display || @campaign.build_player_display
    player_display.transition_type = params[:transition_type]
    player_display.save!

    respond_to do |format|
      format.json { render json: { transition_type: player_display.transition_type } }
      format.turbo_stream { render_gm_status_turbo_stream(player_display) }
      format.html { render_gm_status_turbo_stream(player_display) }
    end
  rescue ArgumentError, ActiveRecord::RecordInvalid => error
    respond_to do |format|
      format.json { render json: { errors: transition_errors_for(error, player_display) }, status: :unprocessable_entity }
      format.turbo_stream { head :unprocessable_entity }
      format.html { head :unprocessable_entity }
    end
  end

  private

  def set_campaign
    @campaign = Campaign.find(params[:campaign_id] || params[:id])
  end

  def image_url_for(image)
    return nil unless image&.file&.attached?
    url_for(image.file)
  end

  def player_display_stream_name
    "player_display_#{@campaign.id}"
  end

  def record_presented_event!(image)
    PresentationEvent.create!(
      event_type: :presented,
      campaign: @campaign,
      image: image,
      image_title: image.title
    )
  end

  def record_cleared_event!
    PresentationEvent.create!(
      event_type: :cleared,
      campaign: @campaign
    )
  end

  def recent_presentation_events(player_display)
    PresentationEvent.recent_for_panel(
      @campaign,
      excluding_image: player_display&.current_image
    )
  end

  def render_gm_panel_turbo_stream(player_display)
    render turbo_stream: [
      gm_panel_header_stream(player_display),
      gm_status_stream(player_display),
      turbo_stream.replace(
        "topbar-status",
        partial: "player_displays/topbar_status",
        locals: { player_display: player_display }
      )
    ]
  end

  def render_gm_panel_controls_turbo_stream(player_display)
    render turbo_stream: [
      gm_panel_header_stream(player_display),
      gm_status_stream(player_display)
    ]
  end

  def render_gm_status_turbo_stream(player_display)
    render turbo_stream: [
      gm_status_stream(player_display)
    ]
  end

  def respond_with_player_display(player_display, broadcast: true)
    payload = player_display_payload(player_display)

    ActionCable.server.broadcast(player_display_stream_name, payload) if broadcast

    respond_to do |format|
      format.json { render json: payload }
      format.turbo_stream { render_gm_panel_turbo_stream(player_display) }
      format.html { render_gm_panel_turbo_stream(player_display) }
    end
  end

  def player_display_payload(player_display)
    {
      image_url: image_url_for(player_display.current_image),
      image_id: player_display.current_image_id,
      image_title: player_display.current_image&.title,
      show_title: player_display.show_title,
      transition_type: player_display.transition_type
    }
  end

  def gm_panel_header_stream(player_display)
    turbo_stream.replace(
      "gm-panel-header",
      partial: "player_displays/gm_panel_header",
      locals: { player_display: player_display }
    )
  end

  def gm_status_stream(player_display)
    turbo_stream.replace(
      "gm-status",
      partial: "player_displays/gm_status",
      locals: {
        player_display: player_display,
        recent_events: recent_presentation_events(player_display)
      }
    )
  end

  def transition_errors_for(error, player_display)
    return error.record.errors.full_messages if error.is_a?(ActiveRecord::RecordInvalid)
    return player_display.errors.full_messages if player_display&.errors&.any?

    [ "Transition type is invalid" ]
  end
end
