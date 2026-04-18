class PlayerDisplayChannel < ActionCable::Channel::Base
  def subscribed
    reject if params[:campaign_id].blank?
    stream_from "player_display_#{params[:campaign_id]}"
  end
end
