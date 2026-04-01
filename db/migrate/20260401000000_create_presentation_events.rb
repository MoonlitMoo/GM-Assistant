class CreatePresentationEvents < ActiveRecord::Migration[8.1]
  def change
    create_table :presentation_events do |t|
      t.references :campaign, null: false, foreign_key: true
      t.references :image, null: true, foreign_key: { on_delete: :nullify }
      t.integer :event_type, null: false, default: 0
      t.string :image_title

      t.timestamps
    end
  end
end
