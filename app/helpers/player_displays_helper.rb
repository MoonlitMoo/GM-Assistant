module PlayerDisplaysHelper
  def gm_panel_breadcrumb(image)
    return nil if image.blank?

    segments = []
    folder = image.album.folder

    while folder.present?
      segments.unshift(folder.name) unless folder.is_root?
      folder = folder.parent
    end

    (segments + [ image.album.name ]).join(" › ")
  end
end
