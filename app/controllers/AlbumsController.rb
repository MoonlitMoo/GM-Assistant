class AlbumsController < ApplicationController
    before_action :set_album, only: [ :show, :edit, :update, :destroy ]
    before_action :set_folder, only: [ :new, :create ], if: -> { params[:folder_id].present? }

    def show
      @images = @album.images.with_attached_file.order(created_at: :desc)
    end

    def new
      @album = @folder.albums.build(campaign: @folder.campaign)
    end

    def create
      @album = @folder.albums.build(album_params)
      @album.campaign = @folder.campaign
      if @album.save
        redirect_to @album, notice: "Album created successfully"
      else
        render :new, status: :unprocessable_entity
      end
    end

    def edit
    end

    def update
      if @album.update(album_params)
        redirect_to @album, notice: "Album updated successfully"
      else
        render :edit, status: :unprocessable_entity
      end
    end

    def destroy
      parent = @album.folder
      @album.destroy
      redirect_to parent, notice: "Album destroyed successfully"
    end

    private

    def set_album
      @album = Album.find(params[:id])
    end

    def set_folder
      @folder = Folder.find(params[:folder_id])
    end

    def album_params
      params.expect(album: [ :name, :description ])
    end
end
