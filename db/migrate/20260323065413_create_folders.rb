class CreateFolders < ActiveRecord::Migration[8.1]
  def change
    create_table :folders do |t|
      t.references :campaign, null: false, foreign_key: true
      t.references :parent, foreign_key: { to_table: :folders }, null: true

      t.string :name, null: false
      t.boolean :is_root, null: false, default: false

      t.timestamps
    end

    add_index :folders, :parent_id
    add_index :folders, :campaign_id

    add_index :folders, [ :campaign_id ], unique: true, where: "is_root = 1", name: "index_folders_one_root_per_campaign"
  end
end
