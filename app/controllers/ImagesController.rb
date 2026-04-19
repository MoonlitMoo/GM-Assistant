class ImagesController < ApplicationController
  include Breadcrumbable

  layout "campaign"
  before_action :set_image, only: [ :show, :edit, :update, :destroy ]
  before_action :set_album, only: [ :new, :create ]
  before_action :set_campaign, only: [ :show, :edit, :update, :new, :create, :destroy ]
  before_action :set_image_show_breadcrumbs, only: [ :show ]
  before_action :set_image_new_breadcrumbs, only: [ :new, :create ]
  before_action :set_image_edit_breadcrumbs, only: [ :edit, :update ]
  after_action :touch_campaign_activity, only: [ :show, :edit, :new, :create, :update, :destroy ]

  def show
    @presenting_image_id = @campaign.player_display&.current_image_id.to_i
  end

  def new
    @image = @album.images.build(campaign: @album.campaign)
    @image.show_title = current_user.default_show_title
  end

  def create
    @image = @album.images.build(image_params)
    @image.campaign = @album.campaign

    if @image.save
      redirect_to @album, notice: "Image uploaded successfully"
    else
      render :new, status: :unprocessable_entity
    end
  end

  def edit
  end

  def update
    if @image.update(image_params)
      respond_to do |format|
        format.html { redirect_to @image, notice: "Image updated successfully" }
        format.json { render json: image_json_payload(@image) }
      end
    else
      respond_to do |format|
        format.html { render :edit, status: :unprocessable_entity }
        format.json { render json: { errors: @image.errors.full_messages }, status: :unprocessable_entity }
      end
    end
  end

  def destroy
    album = @image.album
    @image.destroy

    respond_to do |format|
      format.html { redirect_to album, notice: "Image deleted successfully" }
      format.json { render json: { redirect_url: album_path(album) } }
    end
  end

  private

  def set_image
    @image = Image.joins(:campaign).merge(current_user.campaigns).find(params[:id])
  end

  def set_album
    @album = Album.joins(:campaign).merge(current_user.campaigns).find(params[:album_id])
  end

  def image_params
    params.expect(image: [ :title, :notes, :file, :show_title ])
  end

  def image_json_payload(image)
    {
      id: image.id,
      title: image.title,
      notes: image.notes,
      show_title: image.show_title,
      url: image_path(image),
      edit_url: edit_image_path(image),
      delete_url: image_path(image),
      preview_url: image_preview_url(image)
    }
  end

  def image_preview_url(image)
    return nil unless image.file.attached? && image.file.representable?

    url_for(image.file.representation(resize_to_fill: [ 480, 360 ]))
  end

  def set_campaign
    @campaign = @image&.campaign || @album&.campaign
  end

  def set_image_show_breadcrumbs
    build_breadcrumbs(@image)
  end

  def set_image_new_breadcrumbs
    @breadcrumbs = build_breadcrumbs(@album) + [ [ "Upload Image", new_album_image_path(@album) ] ]
  end

  def set_image_edit_breadcrumbs
    @breadcrumbs = build_breadcrumbs(@image) + [ [ "Edit Image", edit_image_path(@image) ] ]
  end
end
