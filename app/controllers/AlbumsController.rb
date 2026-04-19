class AlbumsController < ApplicationController
  include Breadcrumbable

  layout "campaign"
  before_action :set_album, only: [ :show, :edit, :update, :destroy ]
  before_action :set_folder, only: [ :new, :create ]
  before_action :set_campaign, only: [ :show, :edit, :update, :new, :create, :destroy ]
  before_action :set_album_show_breadcrumbs, only: [ :show ]
  before_action :set_album_new_breadcrumbs, only: [ :new, :create ]
  before_action :set_album_edit_breadcrumbs, only: [ :edit, :update ]
  after_action :touch_campaign_activity, only: [ :show, :edit, :new, :create, :update, :destroy ]

  def show
    @images = @album.images.with_attached_file
    @presenting_image_id = @campaign.player_display&.current_image_id.to_i
    @album_image_grid_payload = @images.map { |image| album_image_card_payload(image) }
  end

  def new
    @album = @folder.albums.build(campaign: @folder.campaign)
  end

  def create
    @album = @folder.albums.build(album_params)
    @album.campaign = @folder.campaign
    if @album.save
      redirect_to @album, notice: "Album created successfully", flash: { tree_refresh: true }
    else
      render :new, status: :unprocessable_entity
    end
  end

  def edit
  end

  def update
    if @album.update(album_params)
      respond_to do |format|
        format.html { redirect_to @album, notice: "Album updated successfully", flash: { tree_refresh: true } }
        format.json { render json: album_json_payload(@album) }
      end
    else
      respond_to do |format|
        format.html { render :edit, status: :unprocessable_entity }
        format.json { render json: { errors: @album.errors.full_messages }, status: :unprocessable_entity }
      end
    end
  end

  def destroy
    redirect_target = album_destroy_redirect_target(@album)
    @album.destroy

    respond_to do |format|
      format.html { redirect_to redirect_target, notice: "Album destroyed successfully", flash: { tree_refresh: true } }
      format.json { render json: { redirect_url: polymorphic_path(redirect_target) } }
    end
  end

  private

  def set_album
    @album = Album.joins(:campaign).merge(current_user.campaigns).find(params[:id])
  end

  def set_folder
    @folder = Folder.joins(:campaign).merge(current_user.campaigns).find(params[:folder_id])
  end

  def set_campaign
    @campaign = @album&.campaign || @folder&.campaign
  end

  def album_json_payload(album)
    {
      id: album.id,
      name: album.name,
      description: album.description,
      url: album_path(album)
    }
  end

  def album_image_card_payload(image)
    {
      id: image.id,
      title: image.title,
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

  def album_destroy_redirect_target(album)
    return album.campaign if album.folder.is_root?

    album.folder
  end

  def album_params
    params.expect(album: [ :name, :description ])
  end

  def set_album_show_breadcrumbs
    build_breadcrumbs(@album)
  end

  def set_album_new_breadcrumbs
    @breadcrumbs = build_breadcrumbs(@folder) + [ [ "New Album", new_folder_album_path(@folder) ] ]
  end

  def set_album_edit_breadcrumbs
    @breadcrumbs = build_breadcrumbs(@album) + [ [ "Edit Album", edit_album_path(@album) ] ]
  end
end
