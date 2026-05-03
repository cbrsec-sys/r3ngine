export type Organization = {
  id: number;
  name: string;
  description: string | null;
  insert_date: string;
  domains: number[];
  project: number | any;
  targets_count?: number;
};

export type CreateOrganizationDTO = {
  name: string;
  description?: string;
  domains: number[];
  project: number;
};

export type UpdateOrganizationDTO = {
  id: number;
  name?: string;
  description?: string;
  domains?: number[];
  project?: number;
};
