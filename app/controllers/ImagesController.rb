class ImagesController < ApplicationController
  layout "campaign"
  before_action :set_image, only: [ :show, :edit, :update, :destroy ]
  before_action :set_album, only: [ :new, :create ]
  before_action :set_campaign, only: [ :show, :edit, :update, :new, :create ]

  def show
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
end
