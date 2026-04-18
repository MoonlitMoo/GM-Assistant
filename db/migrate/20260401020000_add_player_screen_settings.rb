class AddPlayerScreenSettings < ActiveRecord::Migration[8.1]
  def change
    add_column :images, :show_title, :boolean, null: false, default: false

    add_column :player_displays, :show_title, :boolean, null: false, default: false
    add_column :player_displays, :transition_type, :integer, null: false, default: 0
  end
end
