class PlayerDisplaysController < ApplicationController
  before_action :set_campaign

  def present
    if params[:current_image_id].blank?
      render json: { errors: [ "current_image_id is required" ] }, status: :unprocessable_entity
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
      render json: payload
    else
      render json: { errors: @player_display.errors.full_messages }, status: :unprocessable_entity
    end
  rescue ActiveRecord::InvalidForeignKey
    render json: { errors: [ "Current image must exist" ] }, status: :unprocessable_entity
  end

  def clear
    @campaign.player_display&.update!(current_image: nil)

    payload = { cleared: true }

    ActionCable.server.broadcast(player_display_stream_name, payload)
    render json: payload
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
end
