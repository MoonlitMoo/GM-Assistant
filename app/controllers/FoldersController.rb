class FoldersController < ApplicationController
  include Breadcrumbable

  layout "campaign"
  before_action :set_folder, only: [ :show, :edit, :update, :destroy ]
  before_action :set_parent, only: [ :new, :create ]
  before_action :set_campaign, only: [ :show, :edit, :update, :new, :create, :destroy ]
  before_action :set_folder_show_breadcrumbs, only: [ :show ]
  before_action :set_folder_new_breadcrumbs, only: [ :new, :create ]
  before_action :set_folder_edit_breadcrumbs, only: [ :edit, :update ]
  after_action :touch_campaign_activity, only: [ :show, :edit, :new, :create, :update, :destroy ]

  def show
    @child_folders = NaturalNameSort.sort(@folder.child_folders)
    @albums = NaturalNameSort.sort(@folder.albums)
    @direct_image_count = Image.joins(:album).where(albums: { folder_id: @folder.id }).count
  end

  def new
    # Create the folder using the parent found via the before_actions
    @folder = @parent.child_folders.build(campaign: @parent.campaign)
  end

  def create
    @folder = @parent.child_folders.build(folder_params)
    @folder.campaign = @parent.campaign

    if @folder.save
      redirect_to @folder, notice: "Folder created successfully", flash: { tree_refresh: true }
    else
      render :new, status: :unprocessable_entity
    end
  end

  def edit
  end

  def update
    if @folder.update(folder_params)
      respond_to do |format|
        format.html { redirect_to @folder, notice: "Folder updated successfully", flash: { tree_refresh: true } }
        format.json { render json: folder_json_payload(@folder) }
      end
    else
      respond_to do |format|
        format.html { render :edit, status: :unprocessable_entity }
        format.json { render json: { errors: @folder.errors.full_messages }, status: :unprocessable_entity }
      end
    end
  end

  def destroy
    redirect_target = folder_destroy_redirect_target(@folder)
    @folder.destroy

    respond_to do |format|
      format.html { redirect_to redirect_target, notice: "Folder destroyed successfully", flash: { tree_refresh: true } }
      format.json { render json: { redirect_url: polymorphic_path(redirect_target) } }
    end
  end

  private

  def set_folder
    @folder = Folder.joins(:campaign).merge(current_user.campaigns).find(params[:id])
  end

  def set_campaign
    @campaign = @folder&.campaign || @parent&.campaign
  end

  def set_parent
    @parent = Folder.joins(:campaign).merge(current_user.campaigns).find(params[:folder_id])
  end

  def folder_json_payload(folder)
    {
      id: folder.id,
      name: folder.name,
      description: folder.description,
      url: folder_path(folder)
    }
  end

  def folder_destroy_redirect_target(folder)
    parent = folder.parent
    return folder.campaign if parent.nil? || parent.is_root?

    parent
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
