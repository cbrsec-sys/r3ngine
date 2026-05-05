export interface HackerOneProgram {
  id: string;
  type: string;
  attributes: {
    handle: string;
    name: string;
    currency: string;
    profile_picture: string;
    submission_state: string;
    state: string;
    offers_bounties: boolean;
    started_accepting_at: string;
    number_of_reports_for_user: number;
    bounty_earned_for_user: number;
    bookmarked: boolean;
    open_scope?: boolean;
  };
}

export interface StructuredScope {
  id: string;
  type: string;
  attributes: {
    asset_identifier: string;
    asset_type: string;
    eligible_for_submission: boolean;
    instruction?: string;
  };
}

export interface ProgramDetails extends HackerOneProgram {
  relationships: {
    structured_scopes: {
      data: StructuredScope[];
    };
  };
}
