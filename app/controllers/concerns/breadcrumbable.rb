module Breadcrumbable
  extend ActiveSupport::Concern

  private

  def build_breadcrumbs(resource)
    @breadcrumbs = case resource
    when Campaign
      [ [ resource.name, campaign_path(resource) ] ]
    when Folder
      build_breadcrumbs(resource.campaign) + folder_lineage(resource)
    when Album
      build_breadcrumbs(resource.folder) + [ [ resource.name, album_path(resource) ] ]
    when Image
      build_breadcrumbs(resource.album) + [ [ resource.title, image_path(resource) ] ]
    else
      raise ArgumentError, "Unsupported breadcrumb resource: #{resource.class.name}"
    end
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
