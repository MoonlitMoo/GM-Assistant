class AddPreferencesToUsers < ActiveRecord::Migration[8.1]
  def change
    add_column :users, :preferences, :text
  end
end
