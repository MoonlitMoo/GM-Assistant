# syntax=docker/dockerfile:1

ARG RUBY_VERSION=3.4.9

FROM ruby:${RUBY_VERSION}-slim AS builder

WORKDIR /rails

ENV RAILS_ENV=production \
    BUNDLE_WITHOUT=development:test \
    BUNDLE_DEPLOYMENT=1 \
    BUNDLE_PATH=/usr/local/bundle

RUN apt-get update -qq && \
    apt-get install --no-install-recommends -y \
      build-essential \
      ca-certificates \
      curl \
      git \
      libsqlite3-dev \
      libyaml-dev \
      pkg-config && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install --no-install-recommends -y nodejs && \
    rm -rf /var/lib/apt/lists/*

COPY Gemfile Gemfile.lock ./

RUN bundle install && \
    rm -rf ~/.bundle "${BUNDLE_PATH}"/ruby/*/cache "${BUNDLE_PATH}"/ruby/*/bundler/gems/*/.git

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

RUN SECRET_KEY_BASE=dummy bin/vite build && \
    SECRET_KEY_BASE=dummy bin/rails assets:precompile

FROM ruby:${RUBY_VERSION}-slim AS runtime

WORKDIR /rails

ENV RAILS_ENV=production \
    BUNDLE_WITHOUT=development:test \
    BUNDLE_DEPLOYMENT=1 \
    BUNDLE_PATH=/usr/local/bundle

RUN apt-get update -qq && \
    apt-get install --no-install-recommends -y \
      libyaml-0-2 \
      libsqlite3-0 \
      libvips42 && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd --system rails && \
    useradd --system --create-home --gid rails --shell /bin/bash rails

COPY --from=builder /rails /rails
COPY --from=builder /usr/local/bundle /usr/local/bundle

RUN chown -R rails:rails /rails /usr/local/bundle

USER rails

EXPOSE 3000

ENTRYPOINT ["bin/docker-entrypoint"]
CMD ["bin/rails", "server", "-b", "0.0.0.0", "-p", "3000"]
