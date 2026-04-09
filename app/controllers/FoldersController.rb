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
      redirect_to create_redirect_target, notice: "Folder created successfully", flash: { tree_refresh: true }
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
    parent = @folder.parent || @folder.campaign
    @folder.destroy

    respond_to do |format|
      format.html { redirect_to parent, notice: "Folder destroyed successfully", flash: { tree_refresh: true } }
      format.json { head :ok }
    end
  end

  private

  def set_folder
    @folder = Folder.joins(:campaign).merge(Current.user.campaigns).find(params[:id])
  end

  def set_campaign
    @campaign = @folder&.campaign || @parent&.campaign
  end

  def set_parent
    @parent = Folder.joins(:campaign).merge(Current.user.campaigns).find(params[:folder_id])
  end

  def create_redirect_target
    safe_return_to_path(params[:return_to]) || @parent
  end

  def folder_json_payload(folder)
    {
      id: folder.id,
      name: folder.name,
      description: folder.description,
      url: folder_path(folder)
    }
  end

  def safe_return_to_path(path)
    value = path.to_s
    return if value.blank?
    return if value.start_with?("//")
    return unless value.start_with?("/")
    return if value.match?(/[\r\n]/)

    value
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
