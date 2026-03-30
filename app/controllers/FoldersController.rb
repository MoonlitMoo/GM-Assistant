class FoldersController < ApplicationController
  include Breadcrumbable

  layout "campaign"
  before_action :set_folder, only: [ :show, :edit, :update, :destroy ]
  before_action :set_parent_from_folder, only: [ :new, :create ], if: -> { params[:folder_id].present? }
  before_action :set_campaign, only: [ :show, :edit, :update, :new, :create ]
  before_action :set_folder_show_breadcrumbs, only: [ :show ]
  before_action :set_folder_new_breadcrumbs, only: [ :new, :create ]
  before_action :set_folder_edit_breadcrumbs, only: [ :edit, :update ]

  def show
    @child_folders = @folder.child_folders.order(:name)
    @albums = @folder.albums.order(:name)
  end

  def new
    # Create the folder using the parent found via the before_actions
    @folder = @parent.child_folders.build(campaign: @parent.campaign)
  end

  def create
    @folder = @parent.child_folders.build(folder_params)
    @folder.campaign = @parent.campaign

    if @folder.save
      redirect_to @parent, notice: "Folder created successfully", flash: { tree_refresh: true }
    else
      render :new, status: :unprocessable_entity
    end
  end

  def edit
  end

  def update
    if @folder.update(folder_params)
      redirect_to @folder, notice: "Folder updated successfully", flash: { tree_refresh: true }
    else
      render :edit, status: :unprocessable_entity
    end
  end

  def destroy
    parent = @folder.parent || @folder.campaign
    @folder.destroy
    redirect_to parent, notice: "Folder destroyed successfully", flash: { tree_refresh: true }
  end

  private

  def set_folder
    @folder = Folder.find(params[:id])
  end

  def set_campaign
    @campaign = @folder&.campaign || @parent&.campaign
  end

  def set_parent_from_folder
    @parent = Folder.find(params[:folder_id])
  end

  def folder_params
    params.expect(folder: [ :name, :description ])
  end

  def set_folder_show_breadcrumbs
    build_breadcrumbs(@folder)
  end

  def set_folder_new_breadcrumbs
    @breadcrumbs = build_breadcrumbs(@parent) + [ [ "New Folder", new_folder_folder_path(@parent) ] ]
  end

  def set_folder_edit_breadcrumbs
    @breadcrumbs = build_breadcrumbs(@folder) + [ [ "Edit Folder", edit_folder_path(@folder) ] ]
  end
end
