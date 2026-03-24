class CreateAlbums < ActiveRecord::Migration[8.1]
  def change
    create_table :albums do |t|
      t.references :campaign, null: false, foreign_key: true
      t.references :folder, null: false, foreign_key: true

      t.string :name
      t.text :description

      t.timestamps
    end
  end
end
