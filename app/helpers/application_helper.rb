module ApplicationHelper
  def content_body_frame(&block)
    content = safe_join([ breadcrumbs_payload_tag, capture(&block) ])
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
end
