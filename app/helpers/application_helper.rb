module ApplicationHelper
  def content_body_frame(&block)
    content = capture(&block)
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
end
