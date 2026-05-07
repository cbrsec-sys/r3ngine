export const DORK_PATTERNS = {
  files_sensitive: [
    'site:{domain} ext:env',
    'site:{domain} ext:ini',
    'site:{domain} ext:conf',
    'site:{domain} ext:cnf',
    'site:{domain} ext:cfg',
    'site:{domain} ext:yaml',
    'site:{domain} ext:yml',
    'site:{domain} ext:json',
    'site:{domain} ext:log',
    'site:{domain} ext:sql',
    'site:{domain} ext:db',
    'site:{domain} ext:sqlite',
    'site:{domain} ext:bak',
    'site:{domain} ext:backup',
    'site:{domain} ext:old',
    'site:{domain} ext:tmp',
    'site:{domain} ext:swp',
    'site:{domain} ext:gz',
    'site:{domain} ext:tar',
    'site:{domain} ext:zip',
    'site:{domain} ext:rar'
  ],
  credentials_secrets: [
    'site:{domain} "password"',
    'site:{domain} "passwd"',
    'site:{domain} "pwd="',
    'site:{domain} "api_key"',
    'site:{domain} "apikey"',
    'site:{domain} "api-key"',
    'site:{domain} "secret"',
    'site:{domain} "client_secret"',
    'site:{domain} "access_token"',
    'site:{domain} "auth_token"',
    'site:{domain} "aws_access_key_id"',
    'site:{domain} "aws_secret_access_key"',
    'site:{domain} "PRIVATE KEY"',
    'site:{domain} "BEGIN RSA PRIVATE KEY"',
    'site:{domain} "BEGIN OPENSSH PRIVATE KEY"',
    'site:{domain} "db_password"',
    'site:{domain} "database_password"',
    'site:{domain} "connection string"',
    'site:{domain} "mongodb://"',
    'site:{domain} "postgres://"',
    'site:{domain} "redis://"',
    'site:{domain} "ftp://" "password"'
  ],
  directories_indexing: [
    'site:{domain} intitle:"index of"',
    'site:{domain} intitle:"index of" "parent directory"',
    'site:{domain} "index of /admin"',
    'site:{domain} "index of /backup"',
    'site:{domain} "index of /config"',
    'site:{domain} "index of /db"',
    'site:{domain} "index of /logs"',
    'site:{domain} "index of /uploads"',
    'site:{domain} "index of /private"',
    'site:{domain} "index of /tmp"'
  ],
  admin_panels: [
    'site:{domain} inurl:admin',
    'site:{domain} inurl:login',
    'site:{domain} inurl:dashboard',
    'site:{domain} inurl:cpanel',
    'site:{domain} inurl:wp-admin',
    'site:{domain} inurl:administrator',
    'site:{domain} inurl:backend',
    'site:{domain} inurl:console',
    'site:{domain} inurl:manage',
    'site:{domain} intitle:"admin panel"',
    'site:{domain} intitle:"login panel"'
  ],
  debug_errors: [
    'site:{domain} "sql syntax near"',
    'site:{domain} "syntax error in query"',
    'site:{domain} "unexpected token"',
    'site:{domain} "undefined index"',
    'site:{domain} "stack trace"',
    'site:{domain} "exception occurred"',
    'site:{domain} "fatal error"',
    'site:{domain} "debug mode"',
    'site:{domain} "traceback (most recent call last)"'
  ],
  tech_exposure: [
    'site:{domain} inurl:phpinfo',
    'site:{domain} "phpinfo()"',
    'site:{domain} inurl:server-status',
    'site:{domain} inurl:server-info',
    'site:{domain} "Apache Status"',
    'site:{domain} "nginx status"',
    'site:{domain} inurl:actuator',
    'site:{domain} inurl:metrics',
    'site:{domain} inurl:health'
  ],
  api_exposure: [
    'site:{domain} inurl:/api',
    'site:{domain} inurl:/v1/',
    'site:{domain} inurl:/v2/',
    'site:{domain} "swagger"',
    'site:{domain} "swagger-ui"',
    'site:{domain} "openapi.json"',
    'site:{domain} "graphql"',
    'site:{domain} "graphiql"',
    'site:{domain} "api documentation"',
    'site:{domain} "postman_collection"'
  ],
  cloud_storage: [
    'site:s3.amazonaws.com "{domain}"',
    'site:blob.core.windows.net "{domain}"',
    'site:storage.googleapis.com "{domain}"',
    '"{domain}" "amazonaws.com"',
    '"{domain}" "cloudfront.net"',
    '"{domain}" "digitaloceanspaces.com"'
  ],
  ci_cd_devops: [
    'site:{domain} ".git"',
    'site:{domain} ".git/config"',
    'site:{domain} ".svn"',
    'site:{domain} ".hg"',
    'site:{domain} "jenkins"',
    'site:{domain} "gitlab"',
    'site:{domain} "teamcity"',
    'site:{domain} "build logs"',
    'site:{domain} "pipeline"',
    'site:{domain} "circleci"',
    'site:{domain} "travis-ci"'
  ],
  containers_k8s: [
    'site:{domain} "kubernetes"',
    'site:{domain} "k8s"',
    'site:{domain} "docker-compose"',
    'site:{domain} "Dockerfile"',
    'site:{domain} "container logs"',
    'site:{domain} inurl:kube'
  ],
  webshells_backdoors: [
    'site:{domain} inurl:shell',
    'site:{domain} inurl:cmd',
    'site:{domain} inurl:execute',
    'site:{domain} "webshell"',
    'site:{domain} "c99shell"',
    'site:{domain} "r57shell"'
  ]
};

export const generateDorks = (domains: string[]): string => {
  let allDorks: string[] = [];
  
  domains.forEach(domain => {
    Object.values(DORK_PATTERNS).forEach(patterns => {
      patterns.forEach(pattern => {
        allDorks.push(pattern.replace(/{domain}/g, domain));
      });
    });
  });

  return allDorks.join('\n');
};
