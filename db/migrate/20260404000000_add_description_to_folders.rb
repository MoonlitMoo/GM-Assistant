class AddDescriptionToFolders < ActiveRecord::Migration[8.1]
  def change
    add_column :folders, :description, :text
  end
end
