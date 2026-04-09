class CampaignsController < ApplicationController
  include Breadcrumbable

  layout "campaign", only: [ :show, :edit, :update ]
  before_action :set_campaign, only: [ :show, :edit, :update, :destroy, :tree ]
  before_action :set_campaign_show_breadcrumbs, only: [ :show ]
  before_action :set_campaign_edit_breadcrumbs, only: [ :edit, :update ]
  after_action :touch_campaign_activity, only: [ :show, :edit, :create, :update ]

  def index
    @campaigns = Current.user.campaigns.recently_active
  end

  def show
    @root_folder = @campaign.root_folder
    @child_folders = @root_folder ? @root_folder.child_folders.order(:name) : []
    @root_albums = @root_folder ? @root_folder.albums.order(:name) : []
    @recent_images = @campaign.images.includes(:album).order(created_at: :desc).limit(Current.user.dashboard_recent_count)
    @album_count = @campaign.albums.count
    @image_count = @campaign.images.count
  end

  def new
    @campaign = Current.user.campaigns.build
  end

  def create
    @campaign = Current.user.campaigns.build(campaign_params)
    if @campaign.save
      redirect_to @campaign, notice: "Campaign created successfully"
    else
      render :new, status: :unprocessable_entity
    end
  end

  def edit
  end

  def update
    if @campaign.update(campaign_params)
      redirect_to @campaign, notice: "Campaign updated successfully"
    else
      render :edit, status: :unprocessable_entity
    end
  end

  def destroy
    @campaign.destroy
    redirect_to campaigns_path, notice: "Campaign deleted successfully"
  end

  def tree
    root = @campaign.root_folder
    render json: build_folder_tree(root)
  end

  private

  def set_campaign
    @campaign = Current.user.campaigns.find(params[:id])
  end

  def campaign_params
    params.expect(campaign: [ :name, :description ])
  end

  def set_campaign_show_breadcrumbs
    build_breadcrumbs(@campaign)
  end

  def set_campaign_edit_breadcrumbs
    @breadcrumbs = build_breadcrumbs(@campaign) + [ [ "Edit Campaign", edit_campaign_path(@campaign) ] ]
  end

  def build_folder_tree(folder)
    {
      id: folder.id,
      campaignId: folder.campaign_id,
      name: folder.name,
      url: folder_path(folder),
      folders: folder.child_folders.map { |f| build_folder_tree(f) },
      albums: folder.albums.map { |a| { id: a.id, name: a.name, url: album_path(a) } }
    }
  end
end
