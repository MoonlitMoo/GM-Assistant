namespace :invite_codes do
  desc "Generate one-time invite codes"
  task :generate, [ :count ] => :environment do |_task, args|
    count = args[:count].presence&.to_i || 1

    InviteCode.generate!(count: count).each do |token|
      puts token
    end
  end
end
