class PlayerDisplaysController < ApplicationController
  before_action :set_campaign

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
    @player_display.current_image_id = params[:current_image_id]

    if @player_display.save
      payload = {
        image_url: image_url_for(@player_display.current_image),
        image_id: @player_display.current_image_id
      }

      ActionCable.server.broadcast(player_display_stream_name, payload)

      respond_to do |format|
        format.json { render json: payload }
        format.turbo_stream { render_gm_panel_turbo_stream(@player_display) }
        format.html { render_gm_panel_turbo_stream(@player_display) }
      end
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
  end

  def clear
    player_display = @campaign.player_display
    player_display&.update!(current_image: nil)

    payload = { cleared: true }

    ActionCable.server.broadcast(player_display_stream_name, payload)

    respond_to do |format|
      format.json { render json: payload }
      format.turbo_stream { render_gm_panel_turbo_stream(player_display) }
      format.html { render_gm_panel_turbo_stream(player_display) }
    end
  end

  private

  def set_campaign
    @campaign = Campaign.find(params[:campaign_id])
  end

  def image_url_for(image)
    return nil unless image&.file&.attached?
    url_for(image.file)
  end

  def player_display_stream_name
    "player_display_#{@campaign.id}"
  end

  def render_gm_panel_turbo_stream(player_display)
    render turbo_stream: [
      turbo_stream.replace(
        "gm-panel-header",
        partial: "player_displays/gm_panel_header",
        locals: { player_display: player_display }
      ),
      turbo_stream.replace(
        "gm-status",
        partial: "player_displays/gm_status",
        locals: { player_display: player_display }
      )
    ]
  end
end
