class AlbumsController < ApplicationController
  layout "campaign"
  before_action :set_album, only: [ :show, :edit, :update, :destroy ]
  before_action :set_folder, only: [ :new, :create ], if: -> { params[:folder_id].present? }
  before_action :set_campaign, only: [ :show, :edit, :update, :new, :create ]
  before_action :set_album_show_breadcrumbs, only: [ :show ]
  before_action :set_album_new_breadcrumbs, only: [ :new, :create ]
  before_action :set_album_edit_breadcrumbs, only: [ :edit, :update ]

  def show
    @images = @album.images.with_attached_file
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
      redirect_to @album, notice: "Album updated successfully", flash: { tree_refresh: true }
    else
      render :edit, status: :unprocessable_entity
    end
  end

  def destroy
    parent = @album.folder
    @album.destroy
    redirect_to parent, notice: "Album destroyed successfully", flash: { tree_refresh: true }
  end

  private

  def set_album
    @album = Album.find(params[:id])
  end

  def set_folder
    @folder = Folder.find(params[:folder_id])
  end

  def set_campaign
    @campaign = @album&.campaign || @folder&.campaign
  end

  def album_params
    params.expect(album: [ :name, :description ])
  end

  def set_album_show_breadcrumbs
    @breadcrumbs = album_breadcrumbs(@album)
  end

  def set_album_new_breadcrumbs
    @breadcrumbs = folder_breadcrumbs(@folder) + [ [ "New Album", new_folder_album_path(@folder) ] ]
  end

  def set_album_edit_breadcrumbs
    @breadcrumbs = album_breadcrumbs(@album) + [ [ "Edit Album", edit_album_path(@album) ] ]
  end
end
