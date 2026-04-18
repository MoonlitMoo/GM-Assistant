module PlayerDisplaysHelper
  def gm_panel_breadcrumb(image)
    return nil if image.blank?

    (image.album.folder.ancestry.map(&:name) + [ image.album.name ]).join(" › ")
  end
end
