class PlayerController < ApplicationController
  allow_unauthenticated_access

  layout "player"
  before_action :set_campaign

  def show
    @player_display = @campaign.player_display || @campaign.build_player_display
    @current_image = @player_display.current_image
    @current_image_url = current_image_url
  end

  private

  def set_campaign
    @campaign = Campaign.includes(player_display: { current_image: [ file_attachment: :blob ] }).find(params[:id])
  end

  def current_image_url
    return nil unless @current_image&.file&.attached?
    url_for(@current_image.file)
  end
end
