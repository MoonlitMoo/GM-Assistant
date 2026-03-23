class CreateImages < ActiveRecord::Migration[8.1]
  def change
    create_table :images do |t|
      t.references :campaign, null: false, foreign_key: true
      t.references :album, null: false, foreign_key: true

      t.string :title
      t.text :notes

      t.timestamps
    end
  end
end
