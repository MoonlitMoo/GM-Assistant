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

  def form_navigation_params
    current_path = safe_return_to_path(request.fullpath)
    current_path.present? ? { return_to: current_path } : {}
  end

  def form_cancel_path(default_path)
    form_return_to_value || default_path
  end

  def form_return_to_field
    return unless form_return_to_value.present?

    hidden_field_tag :return_to, form_return_to_value
  end

  private

  def form_return_to_value
    safe_return_to_path(params[:return_to])
  end

  def safe_return_to_path(path)
    value = path.to_s
    return if value.blank?
    return if value.start_with?("//")
    return unless value.start_with?("/")
    return if value.match?(/[\r\n]/)

    value
  end
end
