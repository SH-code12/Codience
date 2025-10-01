import type { user } from "../types/UserTest";

interface props {
  userData: user | null;
}
const UserCard = ({ userData }: props) => {
  if (!userData) return null;
  return (
    <div>
      <p>{userData.userId}</p>
      {userData.id}
      {userData.title}
      {userData.completed}
    </div>
  );
};

export default UserCard;
