class AddImageFitToPlayerDisplays < ActiveRecord::Migration[8.1]
  def change
    add_column :player_displays, :image_fit, :string, null: false, default: "contain"
  end
end
