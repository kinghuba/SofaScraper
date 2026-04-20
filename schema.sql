BEGIN;


CREATE TABLE IF NOT EXISTS core.countries
(
    id bigserial NOT NULL,
    iso_alpha2 character(2) COLLATE pg_catalog."default",
    iso_alpha3 character(3) COLLATE pg_catalog."default",
    name text COLLATE pg_catalog."default",
    flag text COLLATE pg_catalog."default",
    CONSTRAINT countries_pkey PRIMARY KEY (id),
    CONSTRAINT countries_iso_alpha2_key UNIQUE (iso_alpha2),
    CONSTRAINT countries_iso_alpha3_key UNIQUE (iso_alpha3)
);

CREATE TABLE IF NOT EXISTS core.scrape_runs
(
    id bigserial NOT NULL,
    sport_id bigint NOT NULL,
    started_at timestamp with time zone NOT NULL DEFAULT now(),
    finished_at timestamp with time zone,
    row_count integer,
    scraper_version text COLLATE pg_catalog."default" NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT scrape_runs_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS core.scrapes
(
    id bigserial NOT NULL,
    sport_id bigint NOT NULL,
    item text COLLATE pg_catalog."default" NOT NULL,
    item_custom_id text COLLATE pg_catalog."default",
    item_slug text COLLATE pg_catalog."default",
    item_url text COLLATE pg_catalog."default",
    scrape_run_id bigint NOT NULL,
    is_date boolean NOT NULL DEFAULT false,
    is_partial boolean NOT NULL DEFAULT false,
    created_at date NOT NULL DEFAULT now(),
    CONSTRAINT scrapes_pkey PRIMARY KEY (id),
    CONSTRAINT scrapes_item_sport_key UNIQUE (item, sport_id)
);

CREATE TABLE IF NOT EXISTS core.sports
(
    id bigserial NOT NULL,
    slug text COLLATE pg_catalog."default" NOT NULL,
    name text COLLATE pg_catalog."default" NOT NULL,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT sports_pkey PRIMARY KEY (id),
    CONSTRAINT sports_slug_key UNIQUE (slug)
);

CREATE TABLE IF NOT EXISTS football.commentary
(
    id bigserial NOT NULL,
    type text COLLATE pg_catalog."default" NOT NULL,
    text text COLLATE pg_catalog."default" NOT NULL,
    period_name text COLLATE pg_catalog."default",
    "time" integer,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT football_commentary_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS football.incidents
(
    id bigserial NOT NULL,
    match_id bigint NOT NULL,
    incident_type text COLLATE pg_catalog."default" NOT NULL,
    incident_class text COLLATE pg_catalog."default" NOT NULL,
    is_home boolean,
    minute smallint,
    added_time smallint,
    period text COLLATE pg_catalog."default",
    goal_scorer_id bigint,
    assist_player_id bigint,
    home_score_after smallint,
    away_score_after smallint,
    carded_player_id bigint,
    rescinded boolean,
    player_in_id bigint,
    player_out_id bigint,
    is_injury_sub boolean,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT football_incidents_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS football.lineups
(
    id bigserial NOT NULL,
    match_id bigint NOT NULL,
    team_id bigint NOT NULL,
    player_id bigint NOT NULL,
    shirt_number smallint,
    "position" text COLLATE pg_catalog."default",
    is_starter boolean NOT NULL DEFAULT true,
    sub_in_minute smallint,
    sub_out_minute smallint,
    is_captain boolean DEFAULT false,
    rating numeric(4, 2),
    rating_alt numeric(4, 2),
    statistics jsonb,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT football_lineups_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS football.managers
(
    id bigserial NOT NULL,
    name text COLLATE pg_catalog."default" NOT NULL,
    slug text COLLATE pg_catalog."default" NOT NULL,
    short_name text COLLATE pg_catalog."default",
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT football_managers_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS football.match_commentary
(
    id bigserial NOT NULL,
    match_id bigint NOT NULL,
    type text COLLATE pg_catalog."default" NOT NULL,
    text text COLLATE pg_catalog."default" NOT NULL,
    "time" integer NOT NULL,
    period_name text COLLATE pg_catalog."default",
    CONSTRAINT football_match_commentary_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS football.match_momentum
(
    id bigserial NOT NULL,
    match_id bigint NOT NULL,
    minute numeric(5, 1) NOT NULL,
    value integer NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT football_match_momentum_pkey PRIMARY KEY (id),
    CONSTRAINT football_match_momentum_unique UNIQUE (match_id, minute)
);

CREATE TABLE IF NOT EXISTS football.match_odds
(
    id bigserial NOT NULL,
    match_id bigint NOT NULL,
    market_name text COLLATE pg_catalog."default" NOT NULL,
    market_group text COLLATE pg_catalog."default",
    period text COLLATE pg_catalog."default",
    choice_name text COLLATE pg_catalog."default" NOT NULL,
    decimal_odds numeric(8, 4),
    fractional_odds text COLLATE pg_catalog."default",
    american_odds integer,
    implied_prob numeric(6, 4),
    true_prob numeric(6, 4),
    true_decimal numeric(8, 4),
    is_winning boolean,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT football_match_odds_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS football.match_scores
(
    match_id bigint NOT NULL,
    home_period1 smallint,
    away_period1 smallint,
    home_period2 smallint,
    away_period2 smallint,
    home_extra1 smallint,
    away_extra1 smallint,
    home_extra2 smallint,
    away_extra2 smallint,
    home_penalties smallint,
    away_penalties smallint,
    home_aggregated smallint,
    away_aggregated smallint,
    injury_time1 smallint,
    injury_time2 smallint,
    injury_time3 smallint,
    injury_time4 smallint,
    scrape_run_id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT football_match_scores_pkey PRIMARY KEY (match_id)
);

CREATE TABLE IF NOT EXISTS football.match_timeseries
(
    id bigserial NOT NULL,
    match_id bigint NOT NULL,
    metric text COLLATE pg_catalog."default" NOT NULL,
    "time" numeric(5, 1) NOT NULL,
    team_id bigint,
    value numeric NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT football_match_timeseries_pkey PRIMARY KEY (id),
    CONSTRAINT football_match_timeseries_unique UNIQUE (match_id, metric, "time", team_id)
);

CREATE TABLE IF NOT EXISTS football.matches
(
    id bigint NOT NULL,
    season_id bigint NOT NULL,
    home_team_id bigint,
    away_team_id bigint,
    venue_id bigint,
    referee_id bigint,
    home_manager_id bigint,
    away_manager_id bigint,
    started_at timestamp with time zone,
    status_code integer NOT NULL,
    status_label text COLLATE pg_catalog."default" NOT NULL,
    round smallint,
    home_score smallint,
    away_score smallint,
    winner_code smallint,
    agg_home_score smallint,
    agg_away_score smallint,
    previous_leg_id bigint,
    scrape_run_id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT football_matches_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS football.players
(
    id bigserial NOT NULL,
    country_id bigint,
    name text COLLATE pg_catalog."default" NOT NULL,
    short_name text COLLATE pg_catalog."default",
    slug text COLLATE pg_catalog."default",
    date_of_birth date,
    height smallint,
    "position" text COLLATE pg_catalog."default",
    proposed_market_value integer,
    proposed_market_currency text COLLATE pg_catalog."default",
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT football_players_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS football.referees
(
    id bigserial NOT NULL,
    country_id bigint,
    slug text COLLATE pg_catalog."default" NOT NULL,
    name text COLLATE pg_catalog."default" NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT football_referees_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS football.seasons
(
    id bigserial NOT NULL,
    tournament_id bigint NOT NULL,
    name text COLLATE pg_catalog."default" NOT NULL,
    year text COLLATE pg_catalog."default",
    scrape_run_id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT football_seasons_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS football.shot_events
(
    id bigserial NOT NULL,
    match_id bigint NOT NULL,
    team_id bigint,
    player_id bigint,
    goalkeeper_id bigint,
    minute smallint,
    added_time smallint,
    period text COLLATE pg_catalog."default",
    shot_type text COLLATE pg_catalog."default",
    situation text COLLATE pg_catalog."default",
    body_part text COLLATE pg_catalog."default",
    player_x numeric(6, 2),
    player_y numeric(6, 2),
    player_z numeric(6, 2),
    goal_mouth_location text COLLATE pg_catalog."default",
    goal_mouth_x numeric(6, 2),
    goal_mouth_y numeric(6, 2),
    goal_mouth_z numeric(6, 2),
    block_x numeric(6, 2),
    block_y numeric(6, 2),
    block_z numeric(6, 2),
    xg numeric(8, 6),
    xgot numeric(8, 6),
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT football_shot_events_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS football.stat_definitions
(
    id bigserial NOT NULL,
    slug text COLLATE pg_catalog."default" NOT NULL,
    name text COLLATE pg_catalog."default" NOT NULL,
    group_name text COLLATE pg_catalog."default",
    stat_type text COLLATE pg_catalog."default" NOT NULL DEFAULT 'positive'::text,
    value_type text COLLATE pg_catalog."default" NOT NULL DEFAULT 'numeric'::text,
    unit text COLLATE pg_catalog."default",
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT football_stat_definitions_pkey PRIMARY KEY (id),
    CONSTRAINT football_stat_definitions_slug_key UNIQUE (slug)
);

CREATE TABLE IF NOT EXISTS football.team_match_stats
(
    id bigserial NOT NULL,
    match_id bigint NOT NULL,
    team_id bigint NOT NULL,
    stat_id bigint NOT NULL,
    period text COLLATE pg_catalog."default" NOT NULL DEFAULT 'ALL'::text,
    value_numeric numeric,
    value_text text COLLATE pg_catalog."default",
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT football_team_match_stats_pkey PRIMARY KEY (id),
    CONSTRAINT football_team_match_stats_unique UNIQUE (match_id, team_id, stat_id, period)
);

CREATE TABLE IF NOT EXISTS football.teams
(
    id bigserial NOT NULL,
    country_id bigint,
    name text COLLATE pg_catalog."default" NOT NULL,
    short_name text COLLATE pg_catalog."default",
    name_code character(3) COLLATE pg_catalog."default",
    slug text COLLATE pg_catalog."default" NOT NULL,
    is_national_team boolean NOT NULL DEFAULT false,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT football_teams_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS football.tournaments
(
    id bigserial NOT NULL,
    country_id bigint,
    name text COLLATE pg_catalog."default" NOT NULL,
    slug text COLLATE pg_catalog."default" NOT NULL,
    priority integer,
    scrape_run_id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT football_tournaments_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS football.venues
(
    id bigserial NOT NULL,
    country_id bigint,
    slug text COLLATE pg_catalog."default" NOT NULL,
    name text COLLATE pg_catalog."default" NOT NULL,
    capacity integer,
    latitude double precision,
    longitude double precision,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT football_venues_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS tennis.game_log
(
    id bigserial NOT NULL,
    match_id bigint NOT NULL,
    set_number smallint NOT NULL,
    game_number smallint NOT NULL,
    home_score smallint,
    away_score smallint,
    serving smallint,
    scoring smallint,
    points jsonb,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT tennis_game_log_pkey PRIMARY KEY (id),
    CONSTRAINT tennis_game_log_unique UNIQUE (match_id, set_number, game_number)
);

CREATE TABLE IF NOT EXISTS tennis.match_momentum
(
    id bigserial NOT NULL,
    match_id bigint NOT NULL,
    set_number smallint NOT NULL,
    game_number smallint NOT NULL,
    value numeric NOT NULL,
    break_occurred boolean NOT NULL DEFAULT false,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT tennis_match_momentum_pkey PRIMARY KEY (id),
    CONSTRAINT tennis_match_momentum_unique UNIQUE (match_id, set_number, game_number)
);

CREATE TABLE IF NOT EXISTS tennis.match_odds
(
    id bigserial NOT NULL,
    match_id bigint NOT NULL,
    market_name text COLLATE pg_catalog."default" NOT NULL,
    market_group text COLLATE pg_catalog."default",
    period text COLLATE pg_catalog."default",
    choice_name text COLLATE pg_catalog."default" NOT NULL,
    decimal_odds numeric(8, 4),
    fractional_odds text COLLATE pg_catalog."default",
    american_odds integer,
    implied_prob numeric(6, 4),
    true_prob numeric(6, 4),
    true_decimal numeric(8, 4),
    is_winning boolean,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT tennis_match_odds_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS tennis.match_stats
(
    id bigserial NOT NULL,
    match_id bigint NOT NULL,
    is_home boolean NOT NULL,
    stat_id bigint NOT NULL,
    period text COLLATE pg_catalog."default" NOT NULL DEFAULT 'ALL'::text,
    value_numeric numeric,
    value_text text COLLATE pg_catalog."default",
    scrape_run_id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT tennis_match_stats_pkey PRIMARY KEY (id),
    CONSTRAINT tennis_match_stats_unique UNIQUE (match_id, is_home, stat_id, period)
);

CREATE TABLE IF NOT EXISTS tennis.matches
(
    id bigint NOT NULL,
    season_id bigint NOT NULL,
    home_player_id bigint,
    away_player_id bigint,
    venue_id bigint,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    status_code integer NOT NULL,
    status_label text COLLATE pg_catalog."default" NOT NULL,
    round_number smallint,
    round_name text COLLATE pg_catalog."default",
    home_seed text COLLATE pg_catalog."default",
    away_seed text COLLATE pg_catalog."default",
    first_to_serve smallint,
    home_sets smallint,
    away_sets smallint,
    winner_code smallint,
    scrape_run_id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT tennis_matches_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS tennis.players
(
    id bigserial NOT NULL,
    country_id bigint,
    name text COLLATE pg_catalog."default" NOT NULL,
    short_name text COLLATE pg_catalog."default",
    slug text COLLATE pg_catalog."default",
    name_code character(3) COLLATE pg_catalog."default",
    gender text COLLATE pg_catalog."default",
    ranking smallint,
    height numeric(4, 2),
    weight smallint,
    plays text COLLATE pg_catalog."default",
    date_of_birth date,
    place_of_birth text COLLATE pg_catalog."default",
    residence text COLLATE pg_catalog."default",
    prize_total_value bigint,
    prize_total_currency text COLLATE pg_catalog."default",
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT tennis_players_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS tennis.rankings
(
    id bigserial NOT NULL,
    player_id bigint NOT NULL,
    match_id bigint NOT NULL,
    tournaments_played integer,
    ranking integer,
    points integer,
    previous_ranking integer,
    previous_points integer,
    best_ranking integer,
    ranking_class text COLLATE pg_catalog."default",
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT tennis_rankings_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS tennis.seasons
(
    id bigserial NOT NULL,
    tournament_id bigint NOT NULL,
    name text COLLATE pg_catalog."default" NOT NULL,
    year smallint NOT NULL,
    is_current boolean NOT NULL DEFAULT false,
    scrape_run_id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT tennis_seasons_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS tennis.set_scores
(
    id bigserial NOT NULL,
    match_id bigint NOT NULL,
    set_number smallint NOT NULL,
    home_games smallint,
    away_games smallint,
    home_tiebreak smallint,
    away_tiebreak smallint,
    duration_secs integer,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT tennis_set_scores_pkey PRIMARY KEY (id),
    CONSTRAINT tennis_set_scores_unique UNIQUE (match_id, set_number)
);

CREATE TABLE IF NOT EXISTS tennis.stat_definitions
(
    id bigserial NOT NULL,
    slug text COLLATE pg_catalog."default" NOT NULL,
    name text COLLATE pg_catalog."default" NOT NULL,
    group_name text COLLATE pg_catalog."default",
    stat_type text COLLATE pg_catalog."default" NOT NULL DEFAULT 'positive'::text,
    value_type text COLLATE pg_catalog."default" NOT NULL DEFAULT 'numeric'::text,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT tennis_stat_definitions_pkey PRIMARY KEY (id),
    CONSTRAINT tennis_stat_definitions_slug_key UNIQUE (slug)
);

CREATE TABLE IF NOT EXISTS tennis.tournaments
(
    id bigserial NOT NULL,
    country_id bigint,
    name text COLLATE pg_catalog."default" NOT NULL,
    slug text COLLATE pg_catalog."default" NOT NULL,
    ground_type text COLLATE pg_catalog."default",
    tennis_points integer,
    flag text COLLATE pg_catalog."default",
    priority integer,
    scrape_run_id bigint NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT tennis_tournaments_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS tennis.venues
(
    id bigserial NOT NULL,
    country_id bigint,
    slug text COLLATE pg_catalog."default" NOT NULL,
    name text COLLATE pg_catalog."default" NOT NULL,
    city text COLLATE pg_catalog."default",
    stadium text COLLATE pg_catalog."default",
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT tennis_venues_pkey PRIMARY KEY (id)
);

ALTER TABLE IF EXISTS core.scrape_runs
    ADD CONSTRAINT scrape_runs_sport_id_fkey FOREIGN KEY (sport_id)
    REFERENCES core.sports (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS core.scrapes
    ADD CONSTRAINT scrapes_scrape_run_id_fkey FOREIGN KEY (scrape_run_id)
    REFERENCES core.scrape_runs (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS core.scrapes
    ADD CONSTRAINT scrapes_sport_id_fkey FOREIGN KEY (sport_id)
    REFERENCES core.sports (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS football.incidents
    ADD CONSTRAINT football_incidents_assist_player_fkey FOREIGN KEY (assist_player_id)
    REFERENCES football.players (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS football.incidents
    ADD CONSTRAINT football_incidents_carded_player_fkey FOREIGN KEY (carded_player_id)
    REFERENCES football.players (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS football.incidents
    ADD CONSTRAINT football_incidents_goal_scorer_fkey FOREIGN KEY (goal_scorer_id)
    REFERENCES football.players (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS football.incidents
    ADD CONSTRAINT football_incidents_match_id_fkey FOREIGN KEY (match_id)
    REFERENCES football.matches (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;
CREATE INDEX IF NOT EXISTS football_incidents_match_id_idx
    ON football.incidents(match_id);


ALTER TABLE IF EXISTS football.incidents
    ADD CONSTRAINT football_incidents_player_in_fkey FOREIGN KEY (player_in_id)
    REFERENCES football.players (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS football.incidents
    ADD CONSTRAINT football_incidents_player_out_fkey FOREIGN KEY (player_out_id)
    REFERENCES football.players (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS football.lineups
    ADD CONSTRAINT football_lineups_match_id_fkey FOREIGN KEY (match_id)
    REFERENCES football.matches (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;
CREATE INDEX IF NOT EXISTS football_lineups_match_id_idx
    ON football.lineups(match_id);


ALTER TABLE IF EXISTS football.lineups
    ADD CONSTRAINT football_lineups_player_id_fkey FOREIGN KEY (player_id)
    REFERENCES football.players (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;
CREATE INDEX IF NOT EXISTS football_lineups_player_id_idx
    ON football.lineups(player_id);


ALTER TABLE IF EXISTS football.lineups
    ADD CONSTRAINT football_lineups_team_id_fkey FOREIGN KEY (team_id)
    REFERENCES football.teams (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS football.match_commentary
    ADD CONSTRAINT football_match_commentary_match_id_fkey FOREIGN KEY (match_id)
    REFERENCES football.matches (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS football.match_momentum
    ADD CONSTRAINT football_match_momentum_match_id_fkey FOREIGN KEY (match_id)
    REFERENCES football.matches (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS football_match_momentum_match_id_idx
    ON football.match_momentum(match_id);


ALTER TABLE IF EXISTS football.match_odds
    ADD CONSTRAINT football_match_odds_match_id_fkey FOREIGN KEY (match_id)
    REFERENCES football.matches (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;
CREATE INDEX IF NOT EXISTS football_match_odds_match_id_idx
    ON football.match_odds(match_id);


ALTER TABLE IF EXISTS football.match_scores
    ADD CONSTRAINT football_match_scores_match_id_fkey FOREIGN KEY (match_id)
    REFERENCES football.matches (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS football_match_scores_pkey
    ON football.match_scores(match_id);


ALTER TABLE IF EXISTS football.match_timeseries
    ADD CONSTRAINT football_match_timeseries_match_id_fkey FOREIGN KEY (match_id)
    REFERENCES football.matches (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS football.match_timeseries
    ADD CONSTRAINT football_match_timeseries_team_id_fkey FOREIGN KEY (team_id)
    REFERENCES football.teams (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS football.matches
    ADD CONSTRAINT football_matches_away_team_fkey FOREIGN KEY (away_team_id)
    REFERENCES football.teams (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;
CREATE INDEX IF NOT EXISTS football_matches_away_team_idx
    ON football.matches(away_team_id);


ALTER TABLE IF EXISTS football.matches
    ADD CONSTRAINT football_matches_home_team_fkey FOREIGN KEY (home_team_id)
    REFERENCES football.teams (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;
CREATE INDEX IF NOT EXISTS football_matches_home_team_idx
    ON football.matches(home_team_id);


ALTER TABLE IF EXISTS football.matches
    ADD CONSTRAINT football_matches_referee_fkey FOREIGN KEY (referee_id)
    REFERENCES football.referees (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS football.matches
    ADD CONSTRAINT football_matches_scrape_run_id_fkey FOREIGN KEY (scrape_run_id)
    REFERENCES core.scrape_runs (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS football.matches
    ADD CONSTRAINT football_matches_season_id_fkey FOREIGN KEY (season_id)
    REFERENCES football.seasons (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;
CREATE INDEX IF NOT EXISTS football_matches_season_idx
    ON football.matches(season_id);


ALTER TABLE IF EXISTS football.matches
    ADD CONSTRAINT football_matches_venue_fkey FOREIGN KEY (venue_id)
    REFERENCES football.venues (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS football.players
    ADD CONSTRAINT football_players_country_id_fkey FOREIGN KEY (country_id)
    REFERENCES core.countries (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS football.referees
    ADD CONSTRAINT football_referees_country_id_fkey FOREIGN KEY (country_id)
    REFERENCES core.countries (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS football.seasons
    ADD CONSTRAINT football_seasons_scrape_run_id_fkey FOREIGN KEY (scrape_run_id)
    REFERENCES core.scrape_runs (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS football.seasons
    ADD CONSTRAINT football_seasons_tournament_id_fkey FOREIGN KEY (tournament_id)
    REFERENCES football.tournaments (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS football.shot_events
    ADD CONSTRAINT football_shot_events_goalkeeper_fkey FOREIGN KEY (goalkeeper_id)
    REFERENCES football.players (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS football.shot_events
    ADD CONSTRAINT football_shot_events_match_id_fkey FOREIGN KEY (match_id)
    REFERENCES football.matches (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;
CREATE INDEX IF NOT EXISTS football_shot_events_match_id_idx
    ON football.shot_events(match_id);


ALTER TABLE IF EXISTS football.shot_events
    ADD CONSTRAINT football_shot_events_player_id_fkey FOREIGN KEY (player_id)
    REFERENCES football.players (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;
CREATE INDEX IF NOT EXISTS football_shot_events_player_id_idx
    ON football.shot_events(player_id);


ALTER TABLE IF EXISTS football.shot_events
    ADD CONSTRAINT football_shot_events_team_id_fkey FOREIGN KEY (team_id)
    REFERENCES football.teams (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS football.team_match_stats
    ADD CONSTRAINT football_team_match_stats_match_id_fkey FOREIGN KEY (match_id)
    REFERENCES football.matches (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;
CREATE INDEX IF NOT EXISTS football_team_match_stats_match_idx
    ON football.team_match_stats(match_id);


ALTER TABLE IF EXISTS football.team_match_stats
    ADD CONSTRAINT football_team_match_stats_stat_id_fkey FOREIGN KEY (stat_id)
    REFERENCES football.stat_definitions (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS football.team_match_stats
    ADD CONSTRAINT football_team_match_stats_team_id_fkey FOREIGN KEY (team_id)
    REFERENCES football.teams (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS football.teams
    ADD CONSTRAINT football_teams_country_id_fkey FOREIGN KEY (country_id)
    REFERENCES core.countries (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS football.tournaments
    ADD CONSTRAINT football_tournaments_country_id_fkey FOREIGN KEY (country_id)
    REFERENCES core.countries (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS football.tournaments
    ADD CONSTRAINT football_tournaments_scrape_run_id_fkey FOREIGN KEY (scrape_run_id)
    REFERENCES core.scrape_runs (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS football.venues
    ADD CONSTRAINT football_venues_country_id_fkey FOREIGN KEY (country_id)
    REFERENCES core.countries (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS tennis.game_log
    ADD CONSTRAINT tennis_game_log_match_id_fkey FOREIGN KEY (match_id)
    REFERENCES tennis.matches (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS tennis_game_log_match_id_idx
    ON tennis.game_log(match_id);


ALTER TABLE IF EXISTS tennis.match_momentum
    ADD CONSTRAINT tennis_match_momentum_match_id_fkey FOREIGN KEY (match_id)
    REFERENCES tennis.matches (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS tennis_match_momentum_match_id_idx
    ON tennis.match_momentum(match_id);


ALTER TABLE IF EXISTS tennis.match_odds
    ADD CONSTRAINT tennis_match_odds_match_id_fkey FOREIGN KEY (match_id)
    REFERENCES tennis.matches (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;
CREATE INDEX IF NOT EXISTS tennis_match_odds_match_id_idx
    ON tennis.match_odds(match_id);


ALTER TABLE IF EXISTS tennis.match_stats
    ADD CONSTRAINT tennis_match_stats_match_id_fkey FOREIGN KEY (match_id)
    REFERENCES tennis.matches (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;
CREATE INDEX IF NOT EXISTS tennis_match_stats_match_id_idx
    ON tennis.match_stats(match_id);


ALTER TABLE IF EXISTS tennis.match_stats
    ADD CONSTRAINT tennis_match_stats_stat_id_fkey FOREIGN KEY (stat_id)
    REFERENCES tennis.stat_definitions (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS tennis.matches
    ADD CONSTRAINT tennis_matches_away_player_fkey FOREIGN KEY (away_player_id)
    REFERENCES tennis.players (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;
CREATE INDEX IF NOT EXISTS tennis_matches_away_player_idx
    ON tennis.matches(away_player_id);


ALTER TABLE IF EXISTS tennis.matches
    ADD CONSTRAINT tennis_matches_home_player_fkey FOREIGN KEY (home_player_id)
    REFERENCES tennis.players (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;
CREATE INDEX IF NOT EXISTS tennis_matches_home_player_idx
    ON tennis.matches(home_player_id);


ALTER TABLE IF EXISTS tennis.matches
    ADD CONSTRAINT tennis_matches_scrape_run_id_fkey FOREIGN KEY (scrape_run_id)
    REFERENCES core.scrape_runs (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS tennis.matches
    ADD CONSTRAINT tennis_matches_season_id_fkey FOREIGN KEY (season_id)
    REFERENCES tennis.seasons (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;
CREATE INDEX IF NOT EXISTS tennis_matches_season_idx
    ON tennis.matches(season_id);


ALTER TABLE IF EXISTS tennis.matches
    ADD CONSTRAINT tennis_matches_venue_id_fkey FOREIGN KEY (venue_id)
    REFERENCES tennis.venues (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS tennis.players
    ADD CONSTRAINT tennis_players_country_id_fkey FOREIGN KEY (country_id)
    REFERENCES core.countries (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS tennis.rankings
    ADD CONSTRAINT tennis_rankings_match_id_fkey FOREIGN KEY (match_id)
    REFERENCES tennis.matches (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS tennis.rankings
    ADD CONSTRAINT tennis_rankingsplayer_id_fkey FOREIGN KEY (player_id)
    REFERENCES tennis.players (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS tennis.seasons
    ADD CONSTRAINT tennis_seasons_scrape_run_id_fkey FOREIGN KEY (scrape_run_id)
    REFERENCES core.scrape_runs (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS tennis.seasons
    ADD CONSTRAINT tennis_seasons_tournament_id_fkey FOREIGN KEY (tournament_id)
    REFERENCES tennis.tournaments (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS tennis.set_scores
    ADD CONSTRAINT tennis_set_scores_match_id_fkey FOREIGN KEY (match_id)
    REFERENCES tennis.matches (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE CASCADE;


ALTER TABLE IF EXISTS tennis.tournaments
    ADD CONSTRAINT tennis_tournaments_country_id_fkey FOREIGN KEY (country_id)
    REFERENCES core.countries (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS tennis.tournaments
    ADD CONSTRAINT tennis_tournaments_scrape_run_id_fkey FOREIGN KEY (scrape_run_id)
    REFERENCES core.scrape_runs (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;


ALTER TABLE IF EXISTS tennis.venues
    ADD CONSTRAINT tennis_venues_country_id_fkey FOREIGN KEY (country_id)
    REFERENCES core.countries (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;

INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1468, NULL, NULL, NULL, 'international');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1134, 'PS', 'PSE', 'Palestine', 'palestine');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1865, 'MF', 'MAF', 'Saint Martin', 'saint-martin-french-part');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1137, 'CG', 'COG', 'Congo Republic', 'congo');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1797, 'SW', 'SXM', 'Sint Maarten', 'sint-maarten-dutch-part');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1128, 'NP', 'NPL', 'Nepal', 'nepal');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1815, 'TO', 'TON', 'Tonga', 'tonga');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (526, 'PA', 'PAN', 'Panama', 'panama');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (31, 'IT', 'ITA', 'Italy', 'italy');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (47, 'PL', 'POL', 'Poland', 'poland');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1469, NULL, NULL, NULL, 'north-and-central-america');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1158, 'ZM', 'ZMB', 'Zambia', 'zambia');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (152, 'RS', 'SRB', 'Serbia', 'serbia');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (11, 'HU', 'HUN', 'Hungary', 'hungary');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (14, 'HR', 'HRV', 'Croatia', 'croatia');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (33, 'BE', 'BEL', 'Belgium', 'belgium');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (18, 'CZ', 'CZE', 'Czechia', 'czech-republic');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (21, 'RU', 'RUS', 'Russia', 'russia');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (23, 'SK', 'SVK', 'Slovakia', 'slovakia');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1685, 'CV', 'CPV', 'Cape Verde', 'cape-verde');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (35, 'NL', 'NLD', 'Netherlands', 'netherlands');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (30, 'DE', 'DEU', 'Germany', 'germany');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (24, 'SI', 'SVN', 'Slovenia', 'slovenia');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (32, 'ES', 'ESP', 'Spain', 'spain');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (86, 'UA', 'UKR', 'Ukraine', 'ukraine');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (66, 'IL', 'ISR', 'Israel', 'israel');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (46, 'TR', 'TUR', 'Türkiye', 'turkey');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (158, 'BA', 'BIH', 'Bosnia & Herzegovina', 'bosnia-herzegovina');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (376, 'AD', 'AND', 'Andorra', 'andorra');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (197, 'LU', 'LUX', 'Luxembourg', 'luxembourg');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (67, 'GR', 'GRC', 'Greece', 'greece');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (7, 'FR', 'FRA', 'France', 'france');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (131, 'WA', 'WAL', 'Wales', 'wales');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1107, 'GN', 'GIN', 'Guinea', 'guinea');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (368, 'ID', 'IDN', 'Indonesia', 'indonesia');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (102, 'CY', 'CYP', 'Cyprus', 'cyprus');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (279, 'MD', 'MDA', 'Moldova', 'moldova');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (85, 'MY', 'MYS', 'Malaysia', 'malaysia');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (44, 'PT', 'PRT', 'Portugal', 'portugal');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (45, 'SG', 'SGP', 'Singapore', 'singapore');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (305, 'EG', 'EGY', 'Egypt', 'egypt');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (938, 'GI', 'GIB', 'Gibraltar', 'gibraltar');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1807, 'GL', 'GRL', 'Greenland', 'greenland');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (257, 'AL', 'ALB', 'Albania', 'albania');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (322, 'ZA', 'ZAF', 'South Africa', 'south-africa');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (339, 'HK', 'HKG', 'Hong Kong', 'hong-kong');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1020, 'BW', 'BWA', 'Botswana', 'botswana');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1090, 'BZ', 'BLZ', 'Belize', 'belize');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (542, 'GH', 'GHA', 'Ghana', 'ghana');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (805, 'KE', 'KEN', 'Kenya', 'kenya');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1136, 'PR', 'PRI', 'Puerto Rico', 'puerto-rico');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (297, 'AZ', 'AZE', 'Azerbaijan', 'azerbaijan');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1628, 'TL', 'TLS', 'East Timor', 'timor-leste');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1457, 'DO', 'DOM', 'Dominican Republic', 'dominican-rep');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (440, 'YE', 'YEM', 'Yemen', 'yemen');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1094, 'KH', 'KHM', 'Cambodia', 'cambodia');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (78, 'BG', 'BGR', 'Bulgaria', 'bulgaria');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1151, 'TZ', 'TZA', 'Tanzania', 'tanzania');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1522, 'DM', 'DMA', 'Dominica', 'dominica');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1139, 'ST', 'STP', 'Sao Tome and Principe', 'sao-tome-and-principe');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (34, 'AU', 'AUS', 'Australia', 'australia');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1459, 'MN', 'MNG', 'Mongolia', 'mongolia');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (310, 'SA', 'SAU', 'Saudi Arabia', 'saudi-arabia');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1556, 'BT', 'BTN', 'Bhutan', 'bhutan');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1091, 'BM', 'BMU', 'Bermuda', 'bermuda');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1106, 'GU', 'GUM', 'Guam', 'guam');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1095, 'KY', 'CYM', 'Cayman Islands', 'cayman-islands');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1924, 'CF', 'CAF', 'Central African Republic', 'central-african-rep');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1804, 'VI', 'VIR', 'US Virgin Islands', 'virgin-islands-us');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1130, 'NI', 'NIC', 'Nicaragua', 'nicaragua');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1795, 'CK', 'COK', 'Cook Islands', 'cook-islands');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1099, 'CW', 'CUW', 'Curacao', 'curacao');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1142, 'SB', 'SLB', 'Solomon Islands', 'solomon-islands');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (512, 'LI', 'LIE', 'Liechtenstein', 'liechtenstein');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1086, 'AW', 'ABW', 'Aruba', 'aruba');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1145, 'LK', 'LKA', 'Sri Lanka', 'sri-lanka');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1612, 'GD', 'GRD', 'Grenada', 'grenada');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1493, 'KN', 'KNA', 'Saint Kitts and Nevis', 'st-kitts-and-nevis');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (26, 'US', 'USA', 'USA', 'usa');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1125, 'MZ', 'MOZ', 'Mozambique', 'mozambique');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (12, 'MX', 'MEX', 'Mexico', 'mexico');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (353, 'QA', 'QAT', 'Qatar', 'qatar');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (485, 'TH', 'THA', 'Thailand', 'thailand');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1135, 'PG', 'PNG', 'Papua New Guinea', 'papua-new-guinea');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (367, 'SV', 'SLV', 'El Salvador', 'el-salvador');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1084, 'AF', 'AFG', 'Afghanistan', 'afghanistan');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (289, 'CR', 'CRI', 'Costa Rica', 'costa-rica');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (13, 'BR', 'BRA', 'Brazil', 'brazil');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (51, 'IE', 'IRL', 'Ireland', 'ireland');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (365, 'GT', 'GTM', 'Guatemala', 'guatemala');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1097, 'TW', 'TWN', 'Chinese Taipei', 'taiwan');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (5, 'NO', 'NOR', 'Norway', 'norway');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1140, 'SC', 'SYC', 'Seychelles', 'seychelles');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (48, 'AR', 'ARG', 'Argentina', 'argentina');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (9, 'SE', 'SWE', 'Sweden', 'sweden');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (19, 'FI', 'FIN', 'Finland', 'finland');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (386, 'ME', 'MNE', 'Montenegro', 'montenegro');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1799, 'YT', 'MYT', 'Mayotte', 'mayotte');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (437, 'HN', 'HND', 'Honduras', 'honduras');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1093, 'BI', 'BDI', 'Burundi', 'burundi');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1141, 'SL', 'SLE', 'Sierra Leone', 'sierra-leone');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1101, 'CD', 'COD', 'DR Congo', 'dr-congo');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1100, 'DJ', 'DJI', 'Djibouti', 'djibouti');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1160, 'ZW', 'ZWE', 'Zimbabwe', 'zimbabwe');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1126, 'MM', 'MMR', 'Myanmar', 'burma');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (52, 'JP', 'JPN', 'Japan', 'japan');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (49, 'CL', 'CHL', 'Chile', 'chile');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (500, 'AO', 'AGO', 'Angola', 'angola');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (391, 'CM', 'CMR', 'Cameroon', 'cameroon');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1153, 'TT', 'TTO', 'Trinidad and Tobago', 'trinidad-and-tobago');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (281, 'VE', 'VEN', 'Venezuela', 'venezuela');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (25, 'CH', 'CHE', 'Switzerland', 'switzerland');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1021, 'RW', 'RWA', 'Rwanda', 'rwanda');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (274, 'CO', 'COL', 'Colombia', 'colombia');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (291, 'KR', 'KOR', 'South Korea', 'south-korea');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (201, 'FO', 'FRO', 'Faroe Islands', 'faroe-islands');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (280, 'PY', 'PRY', 'Paraguay', 'paraguay');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (10, 'IS', 'ISL', 'Iceland', 'iceland');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1467, NULL, NULL, NULL, 'asia');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (92, 'EE', 'EST', 'Estonia', 'estonia');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1143, 'SO', 'SOM', 'Somalia', 'somalia');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (385, 'UZ', 'UZB', 'Uzbekistan', 'uzbekistan');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (163, 'LV', 'LVA', 'Latvia', 'latvia');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (301, 'IR', 'IRN', 'Iran', 'iran');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (502, 'JM', 'JAM', 'Jamaica', 'jamaica');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1481, 'CU', 'CUB', 'Cuba', 'cuba');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (847, 'PH', 'PHL', 'Philippines', 'philippines');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (366, 'VN', 'VNM', 'Vietnam', 'vietnam');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1121, 'MV', 'MDV', 'Maldives', 'maldives');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (165, 'EC', 'ECU', 'Ecuador', 'ecuador');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (388, 'CA', 'CAN', 'Canada', 'canada');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (352, 'IN', 'IND', 'India', 'india');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1146, 'SD', 'SDN', 'Sudan', 'sudan');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (387, 'SM', 'SMR', 'San Marino', 'san-marino');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (160, 'LT', 'LTU', 'Lithuania', 'lithuania');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (99, 'CN', 'CHN', 'China', 'china');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1117, 'LY', 'LBY', 'Libya', 'libya');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1793, 'TC', 'TCA', 'Turks and Caicos Islands', 'turks-and-caicos-islands');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1787, 'AS', 'ASM', 'American Samoa', 'american-samoa');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (331, 'KW', 'KWT', 'Kuwait', 'kuwait');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1150, 'TJ', 'TJK', 'Tajikistan', 'tajikistan');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1113, 'KG', 'KGZ', 'Kyrgyzstan', 'kyrgyzstan');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (428, 'LB', 'LBN', 'Lebanon', 'lebanon');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1103, 'FJ', 'FJI', 'Fiji', 'fiji');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1465, NULL, NULL, NULL, 'europe');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1595, 'AI', 'AIA', 'Anguilla', 'anguilla');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1089, 'BB', 'BRB', 'Barbados', 'barbados');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (379, 'BO', 'BOL', 'Bolivia', 'bolivia');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (148, 'NZ', 'NZL', 'New Zealand', 'new-zealand');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1114, 'LA', 'LAO', 'Laos', 'laos');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (8, 'DK', 'DNK', 'Denmark', 'denmark');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1596, 'GF', 'GUF', 'French Guiana', 'french-guyana');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (17, 'AT', 'AUT', 'Austria', 'austria');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (77, 'RO', 'ROU', 'Romania', 'romania');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1110, 'HT', 'HTI', 'Haiti', 'haiti');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1154, 'TM', 'TKM', 'Turkmenistan', 'turkmenistan');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1022, 'UG', 'UGA', 'Uganda', 'uganda');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1102, 'ET', 'ETH', 'Ethiopia', 'ethiopia');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1104, 'GA', 'GAB', 'Gabon', 'gabon');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1096, 'TD', 'TCD', 'Chad', 'chad');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1105, 'GM', 'GMB', 'Gambia', 'gambia');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (134, 'MT', 'MLT', 'Malta', 'malta');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (159, 'MK', 'MKD', 'North Macedonia', 'macedonia');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1132, 'NG', 'NGA', 'Nigeria', 'nigeria');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (415, 'OM', 'OMN', 'Oman', 'oman');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (351, 'BH', 'BHR', 'Bahrain', 'bahrain');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1470, NULL, NULL, NULL, 'south-america');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (91, 'BY', 'BLR', 'Belarus', 'belarus');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1148, 'SZ', 'SWZ', 'Eswatini', 'swaziland');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1149, 'PF', 'PYF', 'French Polynesia', 'tahiti');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1087, 'BS', 'BHS', 'Bahamas', 'bahamas');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1635, 'MQ', 'MTQ', 'Martinique', 'martinique');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1709, 'VC', 'VCT', 'Saint Vincent and the Grenadines', 'saint-vincent-and-the-grenadines');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1119, 'MG', 'MDG', 'Madagascar', 'madagascar');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (130, 'NX', 'NIR', 'Northern Ireland', 'northern-ireland');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (270, 'GE', 'GEO', 'Georgia', 'georgia');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1466, NULL, NULL, NULL, 'africa');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1112, 'XK', 'XKX', 'Kosovo', 'kosovo');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (57, 'UY', 'URY', 'Uruguay', 'uruguay');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (329, 'JO', 'JOR', 'Jordan', 'jordan');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (20, 'PE', 'PER', 'Peru', 'peru');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (296, 'AM', 'ARM', 'Armenia', 'armenia');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1098, 'KM', 'COM', 'Comoros', 'comoros');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (299, 'AE', 'ARE', 'United Arab Emirates', 'united-arab-emirates');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1123, 'MR', 'MRT', 'Mauritania', 'mauritania');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (378, 'TN', 'TUN', 'Tunisia', 'tunisia');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (2347, 'BQ', 'BES', 'Bonaire', 'bonaire-sint-eustatius-and-saba');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1485, 'BJ', 'BEN', 'Benin', 'benin');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1155, 'VU', 'VUT', 'Vanuatu', 'vanuatu');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1819, 'MP', 'MNP', 'Northern Mariana Islands', 'northern-mariana-islands');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1617, 'BN', 'BRN', 'Brunei', 'brunei');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1124, 'MU', 'MUS', 'Mauritius', 'mauritius');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1109, 'GY', 'GUY', 'Guyana', 'guyana');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1129, 'NC', 'NCL', 'New Caledonia', 'new-caledonia');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1118, 'MO', 'MAC', 'Macao', 'macao');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (960, 'GQ', 'GNQ', 'Equatorial Guinea', 'equatorial-guinea');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (303, 'MA', 'MAR', 'Morocco', 'morocco');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (886, 'SN', 'SEN', 'Senegal', 'senegal');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1147, 'SR', 'SUR', 'Suriname', 'surinam');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1152, 'TG', 'TGO', 'Togo', 'togo');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1115, 'LS', 'LSO', 'Lesotho', 'lesotho');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (304, 'DZ', 'DZA', 'Algeria', 'algeria');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1711, 'VG', 'VGB', 'British Virgin Islands', 'british-virgin-islands');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1111, 'IQ', 'IRQ', 'Iraq', 'iraq');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1131, 'NE', 'NER', 'Niger', 'niger');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (380, 'SY', 'SYR', 'Syria', 'syria');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1108, 'GW', 'GNB', 'Guinea-Bissau', 'guinea-bissau');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1088, 'BD', 'BGD', 'Bangladesh', 'bangladesh');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (390, 'CI', 'CIV', 'Côte d''Ivoire', 'ivory-coast');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1127, 'NA', 'NAM', 'Namibia', 'namibia');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1138, 'WS', 'WSM', 'Samoa', 'samoa');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (2345, 'LC', 'LCA', 'Saint Lucia', 'saint-lucia');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1144, 'SS', 'SSD', 'South Sudan', 'south-sudan');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1092, 'BF', 'BFA', 'Burkina Faso', 'burkina-faso');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (755, 'PK', 'PAK', 'Pakistan', 'pakistan');
INSERT INTO core.countries (id, iso_alpha2, iso_alpha3, name, flag) VALUES (1, 'EN', 'ENG', 'England', 'england');

INSERT INTO core.sports (id, slug, name, is_active, created_at, updated_at) VALUES (1, 'football', 'Football', true);

END;