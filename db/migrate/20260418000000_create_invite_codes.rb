class CreateInviteCodes < ActiveRecord::Migration[8.1]
  def change
    create_table :invite_codes do |t|
      t.string :token, null: false
      t.datetime :used_at
      t.integer :used_by_user_id

      t.timestamps
    end

    add_index :invite_codes, :token, unique: true
    add_index :invite_codes, :used_by_user_id
    add_foreign_key :invite_codes, :users, column: :used_by_user_id
  end
end
