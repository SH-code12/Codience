import { useMemo } from "react";
import { useGitHubProfile } from "../hooks/useGitHubProfile";
import "./styles/Profile.css";

const formatDate = (value: string) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
};

const Profile = () => {
  const username = useMemo(() => localStorage.getItem("User"), []);
  const { profile, loading, error } = useGitHubProfile(username);

  const displayName = profile?.name ?? profile?.login ?? "Profile";
  const emailValue = profile?.email ?? "Not provided";
  const companyValue = profile?.company ?? "Not provided";
  const locationValue = profile?.location ?? "Not provided";
  const blogValue = profile?.blog?.trim() || "Not provided";

  return (
    <main className="profilePage">
      <section className="profileShell">
        <header className="profileHeader">
          <div>
            <h1>Profile</h1>
          </div>

          {profile && (
            <a
              className="profileLink"
              href={profile.html_url}
              target="_blank"
              rel="noreferrer"
            >
              View GitHub
            </a>
          )}
        </header>

        {loading && <div className="profileState">Loading profile...</div>}
        {error && <div className="profileState profileStateError">{error}</div>}

        {profile && (
          <div className="profileGrid">
            <article className="profileSummaryCard">
              <img
                className="profileAvatar"
                src={profile.avatar_url}
                alt={`${displayName} avatar`}
              />

              <h2>{displayName}</h2>
              <p className="profileHandle">@{profile.login}</p>

              {profile.bio && <p className="profileBio">{profile.bio}</p>}

              <div className="profileStatRow">
                <div>
                  <span className="profileStatValue">{profile.public_repos}</span>
                  <span className="profileStatLabel">Public Repos</span>
                </div>
                <div>
                  <span className="profileStatValue">{profile.id}</span>
                  <span className="profileStatLabel">User ID</span>
                </div>
              </div>
            </article>

            <article className="profileInfoCard">
              <div className="profileInfoHeader">
                <h3>Account Details</h3>
                <span>GitHub Profiling</span>
              </div>

              <dl className="profileInfoList">
                <div>
                  <dt>Name</dt>
                  <dd>{displayName}</dd>
                </div>
                <div>
                  <dt>Username</dt>
                  <dd>{profile.login}</dd>
                </div>
                <div>
                  <dt>Email</dt>
                  <dd>{emailValue}</dd>
                </div>
                <div>
                  <dt>Company</dt>
                  <dd>{companyValue}</dd>
                </div>
                <div>
                  <dt>Location</dt>
                  <dd>{locationValue}</dd>
                </div>
                <div>
                  <dt>Website</dt>
                  <dd>{blogValue}</dd>
                </div>
                <div>
                  <dt>Profile URL</dt>
                  <dd>{profile.html_url}</dd>
                </div>
                <div>
                  <dt>Created At</dt>
                  <dd>{formatDate(profile.created_at)}</dd>
                </div>
              </dl>
            </article>
          </div>
        )}
      </section>
    </main>
  );
};

export default Profile;