# This file is auto-generated from the current state of the database. Instead
# of editing this file, please use the migrations feature of Active Record to
# incrementally modify your database, and then regenerate this schema definition.
#
# This file is the source Rails uses to define your schema when running `bin/rails
# db:schema:load`. When creating a new database, `bin/rails db:schema:load` tends to
# be faster and is potentially less error prone than running all of your
# migrations from scratch. Old migrations may fail to apply correctly if those
# migrations use external dependencies or application code.
#
# It's strongly recommended that you check this file into your version control system.

ActiveRecord::Schema[8.1].define(version: 2026_04_04_123548) do
  create_table "active_storage_attachments", force: :cascade do |t|
    t.bigint "blob_id", null: false
    t.datetime "created_at", null: false
    t.string "name", null: false
    t.bigint "record_id", null: false
    t.string "record_type", null: false
    t.index ["blob_id"], name: "index_active_storage_attachments_on_blob_id"
    t.index ["record_type", "record_id", "name", "blob_id"], name: "index_active_storage_attachments_uniqueness", unique: true
  end

  create_table "active_storage_blobs", force: :cascade do |t|
    t.bigint "byte_size", null: false
    t.string "checksum"
    t.string "content_type"
    t.datetime "created_at", null: false
    t.string "filename", null: false
    t.string "key", null: false
    t.text "metadata"
    t.string "service_name", null: false
    t.index ["key"], name: "index_active_storage_blobs_on_key", unique: true
  end

  create_table "active_storage_variant_records", force: :cascade do |t|
    t.bigint "blob_id", null: false
    t.string "variation_digest", null: false
    t.index ["blob_id", "variation_digest"], name: "index_active_storage_variant_records_uniqueness", unique: true
  end

  create_table "albums", force: :cascade do |t|
    t.integer "campaign_id", null: false
    t.datetime "created_at", null: false
    t.text "description"
    t.integer "folder_id", null: false
    t.string "name"
    t.datetime "updated_at", null: false
    t.index ["campaign_id"], name: "index_albums_on_campaign_id"
    t.index ["folder_id"], name: "index_albums_on_folder_id"
  end

  create_table "campaigns", force: :cascade do |t|
    t.datetime "created_at", null: false
    t.text "description"
    t.string "name", null: false
    t.datetime "updated_at", null: false
    t.integer "user_id", null: false
    t.index ["user_id"], name: "index_campaigns_on_user_id"
  end

  create_table "folders", force: :cascade do |t|
    t.integer "campaign_id", null: false
    t.datetime "created_at", null: false
    t.text "description"
    t.boolean "is_root", default: false, null: false
    t.string "name", null: false
    t.integer "parent_id"
    t.datetime "updated_at", null: false
    t.index ["campaign_id"], name: "index_folders_on_campaign_id"
    t.index ["campaign_id"], name: "index_folders_one_root_per_campaign", unique: true, where: "is_root = 1"
    t.index ["parent_id"], name: "index_folders_on_parent_id"
  end

  create_table "images", force: :cascade do |t|
    t.integer "album_id", null: false
    t.integer "campaign_id", null: false
    t.datetime "created_at", null: false
    t.text "notes"
    t.integer "position"
    t.boolean "show_title", default: false, null: false
    t.string "title"
    t.datetime "updated_at", null: false
    t.index ["album_id"], name: "index_images_on_album_id"
    t.index ["campaign_id"], name: "index_images_on_campaign_id"
  end

  create_table "player_displays", force: :cascade do |t|
    t.integer "campaign_id", null: false
    t.datetime "created_at", null: false
    t.integer "current_image_id"
    t.boolean "show_title", default: false, null: false
    t.integer "transition_type", default: 0, null: false
    t.datetime "updated_at", null: false
    t.index ["campaign_id"], name: "index_player_displays_on_campaign_id", unique: true
    t.index ["current_image_id"], name: "index_player_displays_on_current_image_id"
  end

  create_table "presentation_events", force: :cascade do |t|
    t.integer "campaign_id", null: false
    t.datetime "created_at", null: false
    t.integer "event_type", default: 0, null: false
    t.integer "image_id"
    t.string "image_title"
    t.datetime "updated_at", null: false
    t.index ["campaign_id"], name: "index_presentation_events_on_campaign_id"
    t.index ["image_id"], name: "index_presentation_events_on_image_id"
  end

  create_table "sessions", force: :cascade do |t|
    t.datetime "created_at", null: false
    t.string "ip_address"
    t.datetime "updated_at", null: false
    t.string "user_agent"
    t.integer "user_id", null: false
    t.index ["user_id"], name: "index_sessions_on_user_id"
  end

  create_table "users", force: :cascade do |t|
    t.datetime "created_at", null: false
    t.string "email_address", null: false
    t.string "password_digest", null: false
    t.datetime "updated_at", null: false
    t.index ["email_address"], name: "index_users_on_email_address", unique: true
  end

  add_foreign_key "active_storage_attachments", "active_storage_blobs", column: "blob_id"
  add_foreign_key "active_storage_variant_records", "active_storage_blobs", column: "blob_id"
  add_foreign_key "albums", "campaigns"
  add_foreign_key "albums", "folders"
  add_foreign_key "campaigns", "users"
  add_foreign_key "folders", "campaigns"
  add_foreign_key "folders", "folders", column: "parent_id"
  add_foreign_key "images", "albums"
  add_foreign_key "images", "campaigns"
  add_foreign_key "player_displays", "campaigns"
  add_foreign_key "player_displays", "images", column: "current_image_id", on_delete: :nullify
  add_foreign_key "presentation_events", "campaigns"
  add_foreign_key "presentation_events", "images", on_delete: :nullify
  add_foreign_key "sessions", "users"
end
