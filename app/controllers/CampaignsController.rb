class CampaignsController < ApplicationController
  include Breadcrumbable

  layout "campaign", only: [ :show, :edit, :update ]
  before_action :set_campaign, only: [ :show, :edit, :update, :destroy, :tree ]
  before_action :set_campaign_show_breadcrumbs, only: [ :show ]
  before_action :set_campaign_edit_breadcrumbs, only: [ :edit, :update ]
  after_action :touch_campaign_activity, only: [ :show, :edit, :create, :update ]

  def index
    @campaigns = current_user.campaigns.recently_active
  end

  def show
    @root_folder = @campaign.root_folder
    @child_folders = @root_folder ? NaturalNameSort.sort(@root_folder.child_folders) : []
    @root_albums = @root_folder ? NaturalNameSort.sort(@root_folder.albums) : []
    @recent_images = @campaign.images.includes(:album).order(created_at: :desc).limit(current_user.dashboard_recent_count)
    @album_count = @campaign.albums.count
    @image_count = @campaign.images.count
  end

  def new
    @campaign = current_user.campaigns.build
  end

  def create
    @campaign = current_user.campaigns.build(campaign_params)
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
    render json: FolderTree.new(@campaign).as_json
  end

  private

  def set_campaign
    @campaign = current_user.campaigns.find(params[:id])
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
end
