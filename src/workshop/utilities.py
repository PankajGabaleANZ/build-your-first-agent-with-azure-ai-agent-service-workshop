import os
from pathlib import Path

from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import ThreadMessage

from terminal_colors import TerminalColors as tc


class Utilities:
    def log_msg_green(self, msg: str) -> None:
        """Print a message in green."""
        print(f"{tc.GREEN}{msg}{tc.RESET}")

    def log_msg_purple(self, msg: str) -> None:
        """Print a message in purple."""
        print(f"{tc.PURPLE}{msg}{tc.RESET}")

    def log_token_blue(self, msg: str) -> None:
        """Print a token in blue."""
        print(f"{tc.BLUE}{msg}{tc.RESET}", end="", flush=True)

    
        
    async def get_file(self, project_client: AIProjectClient, file_id: str, attachment_name: str) -> str | None:
        """Retrieve the file, save it locally, and return its path."""
        self.log_msg_green(f"Getting file with ID: {file_id}")

        file_name, file_extension = os.path.splitext(
            os.path.basename(attachment_name.split(":")[-1])
        )
        file_name = f"{file_name}.{file_id}{file_extension}"

        env = os.getenv("ENVIRONMENT", "local")
        folder_path = Path(f"{'src/workshop/' if env == 'container' else ''}files/file")
        folder_path.mkdir(parents=True, exist_ok=True)

        file_path = folder_path / file_name

        try:
            file_content_stream = await project_client.agents.get_file_content(file_id)
            
            with file_path.open("wb") as file:
                async for chunk in file_content_stream:
                    if isinstance(chunk, bytes):
                        file.write(chunk)
                    else:
                        print(f"❌ Unexpected data type in file stream: {type(chunk)}")
            
            self.log_msg_green(f"✅ File saved to {file_path}")

            # Cleanup the remote file
            await project_client.agents.delete_file(file_id)

            return str(file_path)  # Return the saved file path

        except Exception as e:
            print(f"❌ Error saving file {file_name}: {e}")
            return None  # Return None in case of failure

    async def get_files(self, message: ThreadMessage, project_client: AIProjectClient) -> None:
        """Get the files from the message and download them."""
        print("Getting files defined by utilities")
        
        # Step 1: Check for the attachments containing file IDs
        if message.attachments:
            for attachment in message.attachments:
                file_id = attachment.get('file_id')  # Get the file ID from the attachment
                
                if file_id:
                    # Extract file name or use "unknown" if not available
                    attachment_name = (
                        "unknown" if not message.file_path_annotations else message.file_path_annotations[0].text
                    )
                    
                    # Step 2: Download the file using the file ID
                    await self.get_file(project_client, file_id, attachment_name)
                    
        print("File retrieval completed")

    async def create_vector_store(self, project_client: AIProjectClient, files: list[str], vector_name_name: str):
        """Upload files to the project and create a vector store."""
        file_ids = []
        
        self.log_msg_purple(f"Starting vector store creation with files: {files}")
        
        # Check if files exist before uploading
        for file in files:
            file_path = Path(file)
            self.log_msg_purple(f"Checking file: {file_path}, exists: {file_path.exists()}")
        
        # Upload the files
        for file in files:
            file_path = Path(file)  # Use the path as is, without prefixes
            self.log_msg_purple(f"Uploading file: {file_path}")
            
            try:
                if not file_path.exists():
                    self.log_msg_purple(f"File does not exist: {file_path}")
                    continue
                    
                self.log_msg_purple(f"File size: {file_path.stat().st_size} bytes")
                file_info = await project_client.agents.upload_file(file_path=file_path, purpose="assistants")
                self.log_msg_purple(f"File uploaded successfully with ID: {file_info.id}")
                file_ids.append(file_info.id)
            except Exception as e:
                self.log_msg_purple(f"Error uploading file {file_path}: {e}")
                continue
        
        if not file_ids:
            self.log_msg_purple("No files were successfully uploaded")
            return None
                
        self.log_msg_purple("Creating the vector store")
        
        try:
            # Create a vector store
            vector_store = await project_client.agents.create_vector_store_and_poll(
                file_ids=file_ids, name=vector_name_name
            )
            
            self.log_msg_purple(f"Vector store created with ID: {vector_store.id}")
            return vector_store
        except Exception as e:
            self.log_msg_purple(f"Error creating vector store: {e}")
            return None
        
    async def update_vector_store(self, project_client: AIProjectClient, vector_store_id: str, files: list[str]):
            """Update the existing vector store with when new files are added."""
            try:
                file_ids = []
                self.log_msg_purple(f"Updating vector store with ID: {vector_store_id} with files: {files}")
                
                # Check if files exist before uploading
                for file in files:
                    file_path = Path(file)
                    self.log_msg_purple(f"Checking file: {file_path}, exists: {file_path.exists()}")
                
                # Upload the files
                for file in files:
                    file_path = Path(file)  # Use the path as is, without prefixes
                    self.log_msg_purple(f"Uploading file: {file_path}")
                    
                    try:
                        if not file_path.exists():
                            self.log_msg_purple(f"File does not exist: {file_path}")
                            continue
                            
                        self.log_msg_purple(f"File size: {file_path.stat().st_size} bytes")
                        file_info = await project_client.agents.upload_file(file_path=file_path, purpose="assistants")
                        self.log_msg_purple(f"File uploaded successfully with ID: {file_info.id}")
                        file_ids.append(file_info.id)
                    except Exception as e:
                        self.log_msg_purple(f"Error uploading file {file_path}: {e}")
                        continue
                
                if not file_ids:
                    self.log_msg_purple("No files were successfully uploaded")
                    return None
                
                # Add files to the existing vector store
                for file_id in file_ids:
                    await project_client.vector_stores.add_file(vector_store_id, file_id)
                
                self.log_msg_purple(f"✅ Updated vector store with ID: {vector_store_id} with new files.")
            except Exception as e:
                self.log_msg_purple(f"❌ Failed to update vector store: {e}")
                raise
    import os
from pathlib import Path

from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import ThreadMessage

from terminal_colors import TerminalColors as tc


class Utilities:
    def log_msg_green(self, msg: str) -> None:
        """Print a message in green."""
        print(f"{tc.GREEN}{msg}{tc.RESET}")

    def log_msg_purple(self, msg: str) -> None:
        """Print a message in purple."""
        print(f"{tc.PURPLE}{msg}{tc.RESET}")

    def log_token_blue(self, msg: str) -> None:
        """Print a token in blue."""
        print(f"{tc.BLUE}{msg}{tc.RESET}", end="", flush=True)
        
    async def get_file(self, project_client: AIProjectClient, file_id: str, attachment_name: str) -> str | None:
        """Retrieve the file, save it locally, and return its path."""
        self.log_msg_green(f"Getting file with ID: {file_id}")

        file_name, file_extension = os.path.splitext(
            os.path.basename(attachment_name.split(":")[-1])
        )
        file_name = f"{file_name}.{file_id}{file_extension}"

        env = os.getenv("ENVIRONMENT", "local")
        folder_path = Path(f"/workspaces/build-your-first-agent-with-azure-ai-agent-service-workshop/files/*")
        folder_path.mkdir(parents=True, exist_ok=True)

        file_path = folder_path / file_name

        try:
            file_content_stream = await project_client.agents.get_file_content(file_id)
            
            # with file_path.open("wb") as file:
            #     async for chunk in file_content_stream:
            #         if isinstance(chunk, bytes):
            #             file.write(chunk)
            #         else:
            #             print(f"❌ Unexpected data type in file stream: {type(chunk)}")
            
            # self.log_msg_green(f"✅ File saved to {file_path}")

            # # Cleanup the remote file
            # await project_client.agents.delete_file(file_id)

            return str(file_content_stream)  # Return the saved file path

        except Exception as e:
            print(f"❌ Error saving file {file_name}: {e}")
            return None  # Return None in case of failure

    async def get_files(self, message: ThreadMessage, project_client: AIProjectClient) -> None:
        """Get the files from the message and download them."""
        print("Getting files defined by utilities")
        
        # Step 1: Check for the attachments containing file IDs
        if message.attachments:
            for attachment in message.attachments:
                file_id = attachment.get('file_id')  # Get the file ID from the attachment
                
                if file_id:
                    # Extract file name or use "unknown" if not available
                    attachment_name = (
                        "unknown" if not message.file_path_annotations else message.file_path_annotations[0].text
                    )
                    
                    # Step 2: Download the file using the file ID
                    await self.get_file(project_client, file_id, attachment_name)
        
        
        print("File retrieval completed")
    async def get_files_with_memory(self, message: ThreadMessage, project_client: AIProjectClient, memory_store: dict = None) -> dict:
        """
        Get the files from the message, download them, and store their contents in memory.
        
        Args:
            message: The message containing file attachments
            project_client: The AIProjectClient instance
            memory_store: Optional existing memory store to update. If None, a new one will be created.
            
        Returns:
            Dictionary mapping file paths to their contents
        """
        if memory_store is None:
            memory_store = {}
        
        print("Getting files and storing contents in memory")
        downloaded_files = []
        
        # Step 1: Check for the attachments containing file IDs
        if message.attachments:
            for attachment in message.attachments:
                file_id = attachment.get('file_id')  # Get the file ID from the attachment
                
                if file_id:
                    # Extract file name or use "unknown" if not available
                    attachment_name = (
                        "unknown" if not message.file_path_annotations else message.file_path_annotations[0].text
                    )
                    
                    # Step 2: Download the file using the file ID
                    file_path = await self.get_file(project_client, file_id, attachment_name)
                    if file_path:
                        downloaded_files.append(file_path)
        
        # Step 3: Store the contents of the downloaded files in memory
        if downloaded_files:
            memory_store = await self.store_file_contents(downloaded_files, memory_store)
        
        print("File retrieval and memory storage completed")
        return memory_store
    
    async def create_vector_store(self, project_client: AIProjectClient, files: list[str], vector_name_name: str):
        """Upload files to the project and create a vector store."""
        file_ids = []
        
        self.log_msg_purple(f"Starting vector store creation with files: {files}")
        
        # Check if files exist before uploading
        for file in files:
            file_path = Path(file)
            self.log_msg_purple(f"Checking file: {file_path}, exists: {file_path.exists()}")
        
        # Upload the files
        for file in files:
            file_path = Path(file)  # Use the path as is, without prefixes
            self.log_msg_purple(f"Uploading file: {file_path}")
            
            try:
                if not file_path.exists():
                    self.log_msg_purple(f"File does not exist: {file_path}")
                    continue
                    
                self.log_msg_purple(f"File size: {file_path.stat().st_size} bytes")
                file_info = await project_client.agents.upload_file(file_path=file_path, purpose="assistants")
                self.log_msg_purple(f"File uploaded successfully with ID: {file_info.id}")
                file_ids.append(file_info.id)
            except Exception as e:
                self.log_msg_purple(f"Error uploading file {file_path}: {e}")
                continue
        
        if not file_ids:
            self.log_msg_purple("No files were successfully uploaded")
            return None
                
        self.log_msg_purple("Creating the vector store")
        
        try:
            # Create a vector store
            vector_store = await project_client.agents.create_vector_store_and_poll(
                file_ids=file_ids, name=vector_name_name
            )
            
            self.log_msg_purple(f"Vector store created with ID: {vector_store.id}")
            return vector_store
        except Exception as e:
            self.log_msg_purple(f"Error creating vector store: {e}")
            return None
        
    async def update_vector_store(self, project_client: AIProjectClient, vector_store_id: str, files: list[str]):
            """Update the existing vector store with when new files are recieved from user."""
            try:
                file_ids = []
                self.log_msg_purple(f"Updating vector store with ID: {vector_store_id} with files: {files}")
                
                # Check if files exist before uploading
                for file in files:
                    file_path = Path(file)
                    self.log_msg_purple(f"Checking file: {file_path}, exists: {file_path.exists()}")
                
                # Upload the files
                for file in files:
                    file_path = Path(file)  # Use the path as is, without prefixes
                    self.log_msg_purple(f"Uploading file: {file_path}")
                    
                    try:
                        if not file_path.exists():
                            self.log_msg_purple(f"File does not exist: {file_path}")
                            continue
                            
                        self.log_msg_purple(f"File size: {file_path.stat().st_size} bytes")
                        file_info = await project_client.agents.upload_file(file_path=file_path, purpose="assistants")
                        self.log_msg_purple(f"File uploaded successfully with ID: {file_info.id}")
                        file_ids.append(file_info.id)
                    except Exception as e:
                        self.log_msg_purple(f"Error uploading file {file_path}: {e}")
                        continue
                
                if not file_ids:
                    self.log_msg_purple("No files were successfully uploaded")
                    return None
                
                # Add files to the existing vector store
                for file_id in file_ids:
                    await project_client.vector_stores.add_file(vector_store_id, file_id)
                
                self.log_msg_purple(f"✅ Updated vector store with ID: {vector_store_id} with new files.")
            except Exception as e:
                self.log_msg_purple(f"❌ Failed to update vector store: {e}")
                raise

    
    async def search_vector_store(self, project_client: AIProjectClient, vector_store_id: str, query: str):
        """Search the vector store for relevant information."""
        self.log_msg_purple(f"Searching vector store with ID: {vector_store_id} for query: {query}")

        try:
            # Perform the search
            search_results = await project_client.vector_stores.search(
                vector_store_id=vector_store_id,
                query=query,
                top_k=5  # Number of top results to return
            )

            if search_results:
                self.log_msg_purple(f"Search results: {search_results}")
                return search_results
            else:
                self.log_msg_purple("No results found")
                return None
        except Exception as e:
            self.log_msg_purple(f"Error searching vector store: {e}")
            return None
        
    