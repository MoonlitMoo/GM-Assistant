class FolderTree
  include Rails.application.routes.url_helpers

  def initialize(campaign)
    @campaign = campaign
  end

  def as_json
    root = folders_by_parent_id[nil]&.first
    return {} unless root

    build_node(root).merge(
      new_root_folder_url: new_folder_path(parent_id: root.id)
    )
  end

  private

  def folders_by_parent_id
    @folders_by_parent_id ||= all_folders.group_by(&:parent_id)
  end

  def albums_by_folder_id
    @albums_by_folder_id ||= all_albums.group_by(&:folder_id)
  end

  def all_folders
    @all_folders ||= @campaign.folders.order(:name).to_a
  end

  def all_albums
    @all_albums ||= @campaign.albums
      .left_outer_joins(:images)
      .select("albums.*, COUNT(images.id) AS image_count")
      .group("albums.id")
      .order(:name)
      .to_a
  end

  def build_node(folder)
    child_folders = folders_by_parent_id[folder.id] || []
    albums = albums_by_folder_id[folder.id] || []

    {
      id: folder.id,
      campaignId: folder.campaign_id,
      name: folder.name,
      url: folder_path(folder),
      edit_url: edit_folder_path(folder),
      new_subfolder_url: new_folder_path(parent_id: folder.id),
      new_album_url: new_album_path(folder_id: folder.id),
      child_folder_count: child_folders.size,
      album_count: albums.size,
      image_count: albums.sum { |album| album_image_count(album) },
      folders: child_folders.map { |child_folder| build_node(child_folder) },
      albums: albums.map { |album| build_album(album) }
    }
  end

  def build_album(album)
    {
      id: album.id,
      name: album.name,
      url: album_path(album),
      edit_url: edit_album_path(album),
      image_count: album_image_count(album)
    }
  end

  def album_image_count(album)
    album.read_attribute(:image_count).to_i
  end
end
