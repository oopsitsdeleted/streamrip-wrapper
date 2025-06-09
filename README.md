
# Streamrip-wrapper

Web wrapper for streamrip's Qobuz track and album search music download functionality

# Setup
You need streamrip installed and in path
```
git clone https://github.com/oopsitsdeleted/streamrip-wrapper.git streamrip-wrapper
cd streamrip-wrapper
pip install flask
```


# Usage
Once the streamrip-wrapper.py is executed, the webpage can be accessed at 127.0.0.1:5000 on a web browser.

The track and album picker allows you to either download tracks or albums from Qobuz. Search the name and click search, then it will give you search results. Click download to download it.

# How it works
When you click search, the backend executes
```
rip search qobuz track '{input name}' --output-file {json_filename}
```
This then saves the search results to the search.json
```
search_track.json example:

[
    {
        "source": "qobuz",
        "media_type": "track",
        "id": "33933680",
        "desc": "Creep by Radiohead"
    }
]
```
The backend then parses this and then the website shows it as options. When an option is selected, it executes 
```
rip id qobuz track '{id}'
```
{id} is from the option that you selected. This then downloads it the option you picked.

So in conclusion, this web wrapper only lets you search and downloads albums and tracks from Qobuz. That is it.

# Conclusion
Yea this was written with Gemeni lol do what you want with it. All credits to streamrip for the actual functionality


