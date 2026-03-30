class CreatePlayerDisplays < ActiveRecord::Migration[8.1]
  def change
    create_table :player_displays do |t|
      t.references :campaign, null: false, foreign_key: true, index: { unique: true }
      t.references :current_image, null: true, foreign_key: { to_table: :images, on_delete: :nullify }

      t.timestamps
    end
  end
end
