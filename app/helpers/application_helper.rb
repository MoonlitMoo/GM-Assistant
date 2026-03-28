module ApplicationHelper
  def content_body_frame(&block)
    parts = [ breadcrumbs_payload_tag ]
    parts << tree_refresh_marker if flash[:tree_refresh]
    parts << capture(&block)

    content = safe_join(parts)
    return content unless turbo_frame_request?

    turbo_frame_tag("content-body", **content_body_frame_options) { content }
  end

  def content_body_frame_options
    {
      data: {
        turbo_action: "advance"
      }
    }
  end

  def breadcrumbs_payload_tag
    tag.div(nil, hidden: true, data: { breadcrumbs_payload: breadcrumbs.to_json })
  end

  def tree_refresh_marker
    tag.div(nil, hidden: true, data: { controller: "tree-refresh" })
  end
end
