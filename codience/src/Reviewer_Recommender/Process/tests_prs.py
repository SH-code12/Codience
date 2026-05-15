test_prs = [
    # flutter 
    {
        "title": "Feature: Implement Biometric Authentication Flow",
        "description": "Added FaceID and Fingerprint support using the local_auth package. Updated the login screen UI to include a biometric toggle.",
        "diff": """
        --- a/lib/screens/login_screen.dart
        +++ b/lib/screens/login_screen.dart
        + Future<void> _authenticateWithBiometrics() async {
        +   bool authenticated = await auth.authenticate(localizedReason: 'Scan to login');
        + }
        """
    },
    # .NET
    {
        "title": "Fix: Optimized SQL Query for User Dashboard",
        "description": "I added an index to the User table and refactored the Entity Framework query to avoid N+1 issues by using Eager Loading.",
        "diff": """
        --- a/Data/UserRepository.cs
        +++ b/Data/UserRepository.cs
        - var users = context.Users.ToList();
        + var users = context.Users.Include(u => u.Posts).AsNoTracking().ToList();
        """
    },
     # React
    {
        "title": "Feat: Migrate Component State to Redux Toolkit",
        "description": "Replacing local useState hooks with a centralized Redux slice to handle global authentication state and improve data consistency.",
        "diff": """
        --- a/src/components/Header.tsx
        +++ b/src/components/Header.tsx
        - const [user, setUser] = useState(null);
        + const user = useSelector((state: RootState) => state.auth.user);
        + const dispatch = useDispatch();
        """
    },
    # DevOps
    {
        "title": "Chore: Multi-stage Docker Build for Production",
        "description": "Optimized image size by implementing a multi-stage build process and moving to alpine-based images for the Nginx frontend.",
        "diff": """
        --- a/Dockerfile
        +++ b/Dockerfile
        + FROM node:20-alpine AS builder
        + WORKDIR /app
        + COPY . .
        + RUN npm run build
        + FROM nginx:alpine
        + COPY --from=builder /app/dist /usr/share/nginx/html
        """
    },
    # Python Backend
    {
        "title": "Feature: Integrate FastAPI Background Tasks",
        "description": "Implemented background worker tasks for processing heavy image uploads without blocking the main request-response cycle.",
        "diff": """
        --- a/app/main.py
        +++ b/app/main.py
        + @app.post("/upload/")
        + async def create_upload_file(background_tasks: BackgroundTasks, file: UploadFile):
        +     background_tasks.add_task(process_image_in_background, file.filename)
        +     return {"message": "Upload started"}
        """
    }
]