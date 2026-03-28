class ApplicationController < ActionController::Base
  # Only allow modern browsers supporting webp images, web push, badges, import maps, CSS nesting, and CSS :has.
  allow_browser versions: :modern

  # Changes to the importmap will invalidate the etag for HTML responses
  stale_when_importmap_changes

  helper_method :breadcrumbs

  private

  def breadcrumbs
    @breadcrumbs || []
  end

  def campaign_breadcrumbs(campaign)
    [ [ campaign.name, campaign_path(campaign) ] ]
  end

  def folder_breadcrumbs(folder)
    campaign_breadcrumbs(folder.campaign) + folder_lineage(folder)
  end

  def album_breadcrumbs(album)
    folder_breadcrumbs(album.folder) + [ [ album.name, album_path(album) ] ]
  end

  def image_breadcrumbs(image)
    album_breadcrumbs(image.album) + [ [ image.title, image_path(image) ] ]
  end

  def folder_lineage(folder)
    lineage = []
    current = folder

    while current.present?
      lineage.unshift([ current.name, folder_path(current) ]) unless current.is_root?
      current = current.parent
    end

    lineage
  end
end
