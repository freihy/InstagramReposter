import instaloader
import json
import pathlib
import os
import base64

class InstaGrabber:

    def __init__(self) -> None:
        # Load from json
        setup_configs = json.load(open('config.json'))
        ig_configs = setup_configs["instagram"]

        self.username = (base64.b64decode((ig_configs["u"]).encode('ascii'))).decode()
        self.password = (base64.b64decode((ig_configs["p"]).encode('ascii'))).decode()
        self.target_account = str(ig_configs["target_account"])
        self.dir_name = ig_configs["first_post_directory_name"]

        # Get instance
        self.l = instaloader.Instaloader()
        # Login using the credentials
        self.l.login(self.username, self.password)
    
    def get_username_data(self, text):
        profile = instaloader.Profile.from_username(self.l.context,text)
        return profile

    def get_first_post(self) -> instaloader.Post:
        posts = instaloader.Profile.from_username(self.l.context, self.target_account).get_posts()
        return next(posts)

    def get_all_post(self) -> instaloader.Post:
        # Use Profile class to access metadata of account
        posts = instaloader.Profile.from_username(self.l.context, self.target_account).get_posts()
        return posts

    def save_post(self, post: instaloader.Post, image_url: str):
        if not os.path.isdir(self.dir_name):
            os.mkdir(self.dir_name)
        # Clears the folder to ensure a clean directory
        self.remove_files()
        # Checks if the post to be saved is a video or a picture
        if post.is_video:
            self.l.download_post(post, target=self.dir_name)
        else:
            self.l.download_post(post, target=self.dir_name)
        # Refactor file names to correct naming convention
        self.refactor_files()

    # Formats all names of files in resource folder to desired name.
    def refactor_files(self):
        path_folder = pathlib.Path(self.dir_name).iterdir()
        for path in path_folder:
            if path.is_file():
                old_extension = path.suffix

                # Might be multiple images, rename the first image only
                try:
                    img_no = int(path.name[:-len(path.suffix)][-1])
                except:
                    img_no = None
                
                if img_no == 1 or img_no == None:
                    directory = path.parent
                    new_name = "first_post" + old_extension
                    path.rename(pathlib.Path(directory, new_name))

    # Removes all files within a directory.
    def remove_files(self):
        dir = self.dir_name
        for f in os.listdir(dir):
            os.remove(os.path.join(dir, f))

if __name__ == "__main__":
    # Load from json
    setup_configs = json.load(open('config.json'))

    # Example execution of printing the caption of the most recent post
    # and saving it's image to image.jpg
    igg = InstaGrabber()
    first_post = igg.get_first_post()

    print(first_post.caption)           # Print caption
    #print(first_post.shortcode)         # Print Instagram URL
    #igg.save_image(first_post.url)      # Save post image
    #igg.save_video(first_post, 'test-test-test') #Saves video post based off hashtag
    igg.save_post(first_post, first_post.url) # Checks if post is either a video or picture format and executes the correct code accordingly.'''

    pass