module ApplicationCable
  class Connection < ActionCable::Connection::Base
    identified_by :current_user

    def connect
      self.current_user = session_user
    end

    private
      def session_user
        Session.find_by(id: cookies.signed[:session_id])&.user
      end
  end
end
