---
layout: post
title: Migrating Jekyll to Amazon S3 and CloudFront
---

This site is now entirely served using Amazon S3/Cloudfront. I'd looked into
doing this a while back, but the lack of TLS support was a no go at the time.
It seems that CloudFront supports using your own SSL certificates for free now,
as long as you don't care about clients that don't support SNI (or you have
money up the wazoo for a dedicated IP).

The set up is mostly self-explanatory, but in typical Amazon fashion, it
requires steps that are bafflingly non-intuitive and/or poorly documented. So,
in the interests of my own documentation, here's what I did:

## S3 setup

1. Create S3 buckets for `chrisdown.name`, with and without the `www` prefix
2. On non-www, set up a bucket policy that allows global read. I use something
   like this (replace `chrisdown.name` with your bucket name):

   <!-- -->

       {
           "Statement": [
               {
                   "Sid": "AllowPublicRead",
                   "Effect": "Allow",
                   "Principal": {
                       "AWS": "*"
                   },
                   "Action": "s3:GetObject",
                   "Resource": "arn:aws:s3:::chrisdown.name/*"
               }
           ]
       }

3. Enable static website hosting
4. Set up the www bucket to redirect to the literal non-www url for your site
   (for example, [https://chrisdown.name](https://chrisdown.name))
5. Set up Jekyll to deploy to S3, here's the [diff][] where I did that

[diff]: https://github.com/cdown/chrisdown.name/commit/aac8e5f0ba01bbf92f5b58ea

## CloudFront setup

1. Upload your SSL certificate(s) to IAM. You can do this using the [aws
   cli][]. According to [the docs][], since the cert will be used for
   CloudFront, it must adhere to the following:

   > If you are uploading a server certificate specifically for use with Amazon
   > CloudFront distributions, you must specify a path using the `--path`
   > option.  The path must begin with `/cloudfront` and must include a
   > trailing slash (for example, `/cloudfront/test/`).

   As such, something like this should work:

       aws iam upload-server-certificate \
           --server-certificate-name chrisdown.name-2014-07 \
           --certificate-body file://chrisdown.name.crt \
           --private-key file://chrisdown.name.key \
           --certificate-chain file://chrisdown.name.chained.crt \
           --path /cloudfront/chrisdown.name-2014-07/

2. Create a new CloudFront distribution that points to the static website
   hosting endpoint for non-www (not the bucket itself). Connect to the origin
   using HTTP only, set viewer protocol to redirect HTTP to HTTPS, add your
   domain name as an alternate CNAME, select your SSL certificate, and set that
   only clients supporting SNI can use HTTPS (otherwise you have to pay for a
   dedicated IP).
3. Do the same for www (this is just used to keep using the same SSL cert)
4. You can test it using openssl's `s_client`:

       openssl s_client \
           -connect foo.cloudfront.net:443 \
           -servername chrisdown.name < /dev/null

[aws cli]: http://aws.amazon.com/cli/
[the docs]: http://docs.aws.amazon.com/IAM/latest/UserGuide/InstallCert.html

## Set up DNS

Since the entry for CloudFront is dynamic, you need to use Route 53. All you
need to do is set up a hosted zone and set up your records, using aliases for
CloudFront endpoints.
