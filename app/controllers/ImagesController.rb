class ImagesController < ApplicationController
  include Breadcrumbable

  layout "campaign"
  before_action :set_image, only: [ :show, :edit, :update, :destroy ]
  before_action :set_album, only: [ :new, :create ]
  before_action :set_campaign, only: [ :show, :edit, :update, :new, :create ]
  before_action :set_image_show_breadcrumbs, only: [ :show ]
  before_action :set_image_new_breadcrumbs, only: [ :new, :create ]
  before_action :set_image_edit_breadcrumbs, only: [ :edit, :update ]

  def show
    @presenting_image_id = @campaign.player_display&.current_image_id.to_i
  end

  def new
    @image = @album.images.build(campaign: @album.campaign)
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
      redirect_to @image, notice: "Image updated successfully"
    else
      render :edit, status: :unprocessable_entity
    end
  end

  def destroy
    album = @image.album
    @image.destroy
    redirect_to album, notice: "Image deleted successfully"
  end

  private

  def set_image
    @image = Image.find(params[:id])
  end

  def set_album
    @album = Album.find(params[:album_id])
  end

  def image_params
    params.expect(image: [ :title, :notes, :file ])
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
