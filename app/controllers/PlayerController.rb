class PlayerController < ApplicationController
  layout "player"
  before_action :set_campaign

  def show
    @current_image_url = current_image_url
  end

  private

  def set_campaign
    @campaign = Campaign.includes(player_display: { current_image: [ file_attachment: :blob ] }).find(params[:id])
  end

  def current_image_url
    current_image = @campaign.player_display&.current_image
    return nil unless current_image&.file&.attached?
    url_for(current_image.file)
  end
end
