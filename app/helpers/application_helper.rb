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

  def resource_form(record:, form_model:, kicker:, title:, cancel_path:, form_url: nil, &block)
    form_options = {
      model: form_model,
      class: "resource-form",
      data: { controller: "submit-shortcut", action: "keydown->submit-shortcut#submit" }
    }
    form_options[:url] = form_url if form_url.present?

    content_tag(:section, class: "record-shell form-shell") do
      content_tag(:div, class: "record-panel form-panel") do
        safe_join([
          resource_form_header(kicker:, title:),
          form_with(**form_options) do |form|
            safe_join([
              form_return_to_field,
              resource_form_errors(record),
              capture(form, &block)
            ].compact)
          end
        ])
      end
    end
  end

  def resource_form_actions(form, record:, noun:, cancel_path:)
    submit_label = record.persisted? ? "Save #{noun}" : "Create #{noun}"

    content_tag(:div, class: "resource-form__actions") do
      safe_join([
        form.submit(submit_label, class: "fantasy-button fantasy-button--primary"),
        link_to("Cancel", cancel_path, class: "resource-form__cancel")
      ])
    end
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

  def resource_form_header(kicker:, title:)
    content_tag(:div, class: "form-panel__header") do
      safe_join([
        content_tag(:p, kicker, class: "record-kicker"),
        content_tag(:h1, title, class: "record-title")
      ])
    end
  end

  def resource_form_errors(record)
    return unless record.errors.any?

    content_tag(:div, class: "form-errors") do
      safe_join([
        content_tag(:h2, "#{pluralize(record.errors.count, "error")} prevented this #{record.model_name.human.downcase} from being saved:"),
        content_tag(:ul) do
          safe_join(record.errors.full_messages.map { |message| content_tag(:li, message) })
        end
      ])
    end
  end
end
