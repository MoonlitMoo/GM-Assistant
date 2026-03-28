class CampaignsController < ApplicationController
  layout "campaign", only: [ :show, :edit, :update ]
  before_action :set_campaign, only: [ :show, :edit, :update, :destroy ]
  before_action :set_campaign_show_breadcrumbs, only: [ :show ]
  before_action :set_campaign_edit_breadcrumbs, only: [ :edit, :update ]

  def index
    @campaigns = Campaign.order(created_at: :desc)
  end

  def show
    @root_folder = @campaign.root_folder
  end

  def new
    @campaign = Campaign.new
  end

  def create
    @campaign = Campaign.new(campaign_params)
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
    @campaign = Campaign.find(params[:id])
    root = @campaign.root_folder
    render json: build_folder_tree(root)
  end

  private

  def set_campaign
    @campaign = Campaign.find(params[:id])
  end

  def campaign_params
    params.expect(campaign: [ :name, :description ])
  end

  def set_campaign_show_breadcrumbs
    @breadcrumbs = campaign_breadcrumbs(@campaign)
  end

  def set_campaign_edit_breadcrumbs
    @breadcrumbs = campaign_breadcrumbs(@campaign) + [ [ "Edit Campaign", edit_campaign_path(@campaign) ] ]
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
