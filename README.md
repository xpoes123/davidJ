# David Jiang — Personal Website

Personal website for David Jiang. Static HTML/CSS/JS site — no build step required.

---

## Local Development

Open `index.html` directly in a browser, or spin up a local server to avoid any
same-origin quirks with `fetch`:

```bash
python3 -m http.server 8080
# then visit http://localhost:8080
```

---

## VPS Deployment

Tested on Ubuntu 22.04 with Nginx. Assumes you have SSH access and `sudo` rights.

1. **Install Nginx**

   ```bash
   sudo apt update && sudo apt install nginx
   ```

2. **Clone the repo**

   ```bash
   sudo git clone <repo-url> /var/www/davidj
   ```

3. **Install the Nginx config**

   ```bash
   sudo cp /var/www/davidj/nginx/davidj.conf /etc/nginx/sites-available/davidj
   sudo ln -s /etc/nginx/sites-available/davidj /etc/nginx/sites-enabled/davidj
   sudo rm -f /etc/nginx/sites-enabled/default
   ```

4. **Set your domain**

   Edit `/etc/nginx/sites-available/davidj` and replace `server_name _;` with
   your actual domain, e.g. `server_name davidjiang.com www.davidjiang.com;`.

5. **Test and reload**

   ```bash
   sudo nginx -t && sudo systemctl reload nginx
   ```

6. **(Optional) HTTPS with Let's Encrypt**

   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d yourdomain.com
   ```

   Certbot will patch the config and set up automatic renewal.

---

## Deploying Updates

Pull the latest code and reload Nginx in one command:

```bash
sudo bash /var/www/davidj/deploy.sh
```

To automate, add a cron job (`sudo crontab -e`) or wire up a webhook that triggers
this script on every push to `main`.

---

## Project Structure

```
index.html        Homepage
blog.html         Blog listing page
projects.html     Projects page
research.html     Research / papers page
img/              Photos and general images
  blogs/          Blog post images
papers/           PDF research papers
posts/            Blog post content (Markdown)
thumbnails/       Thumbnail images for cards
topics.json       Tag / topic data for the blog
nginx/davidj.conf Nginx server block config
deploy.sh         Deployment script
```
