import PRsTable from "../components/PRsTable";
import "./styles/Home.css";
const Home = () => {
  const prs = [
    {
      pr_id: 1,
      pr_title: "first",
      repo_id: 2,
      auhtor: "Ali",
      status: "open",
      risk_score: 30,
      priority_score: 40,
    },
    {
      pr_id: 1,
      pr_title: "second",
      repo_id: 2,
      auhtor: "Mohammed",
      status: "close",
      risk_score: 10,
      priority_score: 20,
    },
    {
      pr_id: 1,
      pr_title: "third",
      repo_id: 2,
      auhtor: "Mohsen",
      status: "open",
      risk_score: 100,
      priority_score: 70,
    },
    {
      pr_id: 1,
      pr_title: "fourth",
      repo_id: 2,
      auhtor: "Fadi",
      status: "open",
      risk_score: 20,
      priority_score: 100,
    },
    {
      pr_id: 1,
      pr_title: "fifth",
      repo_id: 2,
      auhtor: "Mohsen",
      status: "open",
      risk_score: 30,
      priority_score: 50,
    },
    {
      pr_id: 1,
      pr_title: "sixth",
      repo_id: 2,
      auhtor: "Mohsen",
      status: "open",
      risk_score: 30,
      priority_score: 50,
    },
    {
      pr_id: 1,
      pr_title: "seventh",
      repo_id: 2,
      auhtor: "Mohsen",
      status: "open",
      risk_score: 30,
      priority_score: 50,
    },
    {
      pr_id: 1,
      pr_title: "first",
      repo_id: 2,
      auhtor: "Mohsen",
      status: "open",
      risk_score: 30,
      priority_score: 40,
    },
    {
      pr_id: 1,
      pr_title: "first",
      repo_id: 2,
      auhtor: "Mohsen",
      status: "close",
      risk_score: 10,
      priority_score: 20,
    },
    {
      pr_id: 1,
      pr_title: "first",
      repo_id: 2,
      auhtor: "Mohsen",
      status: "open",
      risk_score: 100,
      priority_score: 70,
    },
    {
      pr_id: 1,
      pr_title: "first",
      repo_id: 2,
      auhtor: "Mohsen",
      status: "open",
      risk_score: 20,
      priority_score: 100,
    },
    {
      pr_id: 1,
      pr_title: "first",
      repo_id: 2,
      auhtor: "Mohsen",
      status: "open",
      risk_score: 30,
      priority_score: 50,
    },
    {
      pr_id: 1,
      pr_title: "first",
      repo_id: 2,
      auhtor: "Mohsen",
      status: "open",
      risk_score: 30,
      priority_score: 50,
    },
    {
      pr_id: 1,
      pr_title: "first",
      repo_id: 2,
      auhtor: "Mohsen",
      status: "open",
      risk_score: 30,
      priority_score: 50,
    },
  ];
  let openPrs: number = 0;
  let highPriority: number = 0;
  let highRisk: number = 0;

  prs.forEach((element) => {
    if (element.status == "open") openPrs++;
    if (element.risk_score > 60) highRisk++;
    if (element.priority_score > 60) highPriority++;
  });
  return (
    <div className="home">
      <h2 className="projectTitle">ProjectName</h2>
      <div className="cardsContainer">
        <div className="card open">
          <p>Open Prs</p>
          <span>{openPrs}</span>
        </div>
        <div className="card priority">
          <p>High Priority</p>
          <span>{highPriority}</span>
        </div>
        <div className="card risk">
          <p>High Risk</p>
          <span>{highRisk}</span>
        </div>
      </div>
      <h2 className="tableCaption">Pull Requests</h2>
      <PRsTable prs={prs} />
    </div>
  );
};

export default Home;
